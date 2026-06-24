"""GitHub Search API 客户端。

支持：
- 使用 GITHUB_TOKEN 提升配额
- 分页拉取
- 速率限制重试
- 统一的仓库元数据归一化
"""

import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

GITHUB_API = "https://api.github.com"
SEARCH_REPOS = f"{GITHUB_API}/search/repositories"


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 GET 请求，遇到 403 速率限制时自动重试。"""
        retries = 0
        max_retries = 5
        while True:
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 403 and retries < max_retries:
                # 尝试读取 Retry-After 或 x-ratelimit-reset
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    sleep_sec = int(retry_after)
                else:
                    reset_ts = resp.headers.get("X-RateLimit-Reset")
                    if reset_ts:
                        sleep_sec = max(1, int(reset_ts) - int(time.time()) + 1)
                    else:
                        sleep_sec = 60
                print(f"[GitHub] 命中速率限制，等待 {sleep_sec}s 后重试 ({retries + 1}/{max_retries})")
                time.sleep(min(sleep_sec, 120))  # 最多等 2 分钟
                retries += 1
                continue

            resp.raise_for_status()
            raise RuntimeError(f"GitHub API 返回非 200 状态码: {resp.status_code}")

    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
        max_pages: int = 3,
    ) -> list[dict[str, Any]]:
        """分页搜索仓库，返回归一化后的仓库列表。"""
        results: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": per_page,
                "page": page,
            }
            data = self._get(SEARCH_REPOS, params)
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                repo = self._normalize(item)
                if repo:
                    results.append(repo)

            # GitHub Search API 最多 1000 条，超过则停止
            total_count = data.get("total_count", 0)
            if page * per_page >= total_count or page >= max_pages:
                break

        return results

    def _normalize(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """把 GitHub API 返回的仓库信息整理成我们需要的字段。"""
        full_name = item.get("full_name")
        if not full_name:
            return None

        created_at = item.get("created_at")
        updated_at = item.get("updated_at")
        pushed_at = item.get("pushed_at")

        stars = int(item.get("stargazers_count") or 0)
        forks = int(item.get("forks_count") or 0)
        watchers = int(item.get("watchers_count") or 0)
        open_issues = int(item.get("open_issues_count") or 0)

        age_days = self._days_since(created_at) or 1
        # 日均 star 增速（用于估算近期热度）
        star_velocity = round(stars / age_days, 2)

        return {
            "full_name": full_name,
            "name": item.get("name"),
            "owner": item.get("owner", {}).get("login"),
            "html_url": item.get("html_url"),
            "description": (item.get("description") or "").strip(),
            "language": item.get("language") or "Unknown",
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "open_issues": open_issues,
            "topics": item.get("topics") or [],
            "created_at": created_at,
            "updated_at": updated_at,
            "pushed_at": pushed_at,
            "age_days": age_days,
            "star_velocity": star_velocity,
            "raw": item,
        }

    @staticmethod
    def _days_since(iso_time: str | None) -> int | None:
        if not iso_time:
            return None
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max(1, (now - dt).days)
        except Exception:
            return None
