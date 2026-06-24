#!/usr/bin/env python3
"""AI Hunter Daily 主入口。

用法：
    python run.py
    GITHUB_TOKEN=your_token python run.py
"""

import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent / "src"))

from github_client import GitHubClient
from reporter import DailyReporter
from scorer import ProjectScorer


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_query(base_query: str, updated_after: str | None) -> str:
    """如果查询中未包含 pushed:，追加 pushed_after 过滤。"""
    q = base_query.strip()
    if updated_after and "pushed:" not in q:
        q = f"{q} pushed:>{updated_after}"
    return q


def main() -> int:
    config = load_config()

    client = GitHubClient()
    scorer = ProjectScorer(config)
    reporter = DailyReporter(config)

    search_cfg = config["search"]
    max_pages = search_cfg.get("max_pages", 3)
    per_page = search_cfg.get("per_page", 30)
    sort = search_cfg.get("sort", "stars")
    order = search_cfg.get("order", "desc")
    pushed_after = search_cfg.get("pushed_after")

    all_repos = []
    print("=" * 60)
    print("AI Hunter Daily 开始运行")
    print("=" * 60)

    for query_item in search_cfg["queries"]:
        name = query_item["name"]
        q = build_query(query_item["q"], pushed_after)
        print(f"\n🔍 搜索分类：{name}")
        print(f"   查询：{q}")

        try:
            repos = client.search_repositories(
                query=q,
                sort=sort,
                order=order,
                per_page=per_page,
                max_pages=max_pages,
            )
            print(f"   获取 {len(repos)} 条结果")
            all_repos.extend(repos)
        except Exception as e:
            print(f"   ⚠️ 搜索失败：{e}")
            continue

    if not all_repos:
        print("\n❌ 未获取到任何仓库，请检查网络或 GitHub API 配额。")
        return 1

    print(f"\n📦 去重前总计 {len(all_repos)} 条，开始评分...")
    top_repos = scorer.score(all_repos)
    print(f"✅ 评分完成，精选 Top {len(top_repos)} 个项目")

    report_path = reporter.generate(top_repos)
    print(f"\n📝 日报已生成：{os.path.abspath(report_path)}")
    print("\n🏆 今日 Top 5：")
    for i, r in enumerate(top_repos[:5], start=1):
        print(f"   {i}. {r['full_name']} — {r['total_score']:.1f} 分")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
