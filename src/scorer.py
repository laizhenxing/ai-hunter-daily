"""项目评分与筛选。"""

from datetime import datetime, timezone
from typing import Any


def _days_since(iso_time: str | None) -> int | None:
    if not iso_time:
        return None
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def _count_matches(text: str, keywords: list[str]) -> int:
    text = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text)


class ProjectScorer:
    def __init__(self, config: dict[str, Any]):
        self.weights = config["scoring"]["weights"]
        self.core_topics = [t.lower() for t in config["scoring"]["core_topics"]]
        self.value_keywords = [k.lower() for k in config["scoring"]["value_keywords"]]
        self.top_n = config["scoring"]["top_n"]

    def deduplicate(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按 full_name 去重，保留 star 数更高的版本。"""
        seen: dict[str, dict[str, Any]] = {}
        for repo in repos:
            key = repo["full_name"]
            if key not in seen or repo["stars"] > seen[key]["stars"]:
                seen[key] = repo
        return list(seen.values())

    def score(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """对仓库列表评分、排序，并追加得分与推荐理由。"""
        repos = self.deduplicate(repos)

        # 预先计算辅助指标
        for repo in repos:
            repo["score_breakdown"] = self._breakdown(repo)
            base_score = sum(repo["score_breakdown"].values())
            bonus = self._bonus(repo)
            repo["bonus"] = bonus
            repo["total_score"] = round(base_score + bonus, 1)
            repo["recommendation"] = self._recommendation(repo)

        repos.sort(key=lambda r: r["total_score"], reverse=True)
        return repos[: self.top_n]

    def _bonus(self, repo: dict[str, Any]) -> float:
        """额外加分项：年轻项目 + 黑马爆发系数。"""
        bonus = 0.0

        # 年轻项目奖励
        age = repo.get("age_days", 365)
        if age <= 90:
            bonus += 10
        elif age <= 180:
            bonus += 5

        # 黑马系数：日均 star 增量占总 star 的比例，反映新项目的爆发力
        stars = max(repo.get("stars", 1), 1)
        breakout = (repo.get("star_velocity", 0) / stars) * 100
        if breakout >= 5:  # 日均增长超过总 star 的 5%
            bonus += 10
        elif breakout >= 2:
            bonus += 5

        return bonus

    def _breakdown(self, repo: dict[str, Any]) -> dict[str, float]:
        # 每个维度先归一化到 0-100，再乘以权重，最终总分也是 0-100

        # 1. 7 日 star 增速得分：日均增量 * 7，封顶 100
        sv_7d = min(repo.get("star_velocity", 0) * 7, 100)

        # 2. 24h star 增速得分：日均增量，封顶 100
        sv_24h = min(repo.get("star_velocity", 0), 100)

        # 3. forks 得分：5000 forks 封顶 100
        forks_score = min(repo.get("forks", 0) / 50, 100)

        # 4. 近期更新得分：30 天内更新得 100，否则 0
        days_since_push = _days_since(repo.get("pushed_at"))
        recent_score = 100 if days_since_push is not None and days_since_push <= 30 else 0

        # 5. topic 命中得分：命中 5 个封顶 100
        topics = [t.lower() for t in repo.get("topics", [])]
        topic_hits = sum(1 for t in topics if t in self.core_topics)
        topic_score = min(topic_hits * 20, 100)

        # 6. 关键词命中得分：命中 5 个封顶 100
        searchable = f"{repo.get('name', '')} {repo.get('description', '')}"
        keyword_hits = _count_matches(searchable, self.value_keywords)
        keyword_score = min(keyword_hits * 20, 100)

        weights = self.weights
        return {
            "star_velocity_7d": round(sv_7d * weights["star_velocity_7d"], 2),
            "star_velocity_24h": round(sv_24h * weights["star_velocity_24h"], 2),
            "forks": round(forks_score * weights["forks"], 2),
            "recent_update": round(recent_score * weights["recent_update"], 2),
            "topic_match": round(topic_score * weights["topic_match"], 2),
            "keyword_match": round(keyword_score * weights["keyword_match"], 2),
        }

    def _recommendation(self, repo: dict[str, Any]) -> str:
        reasons: list[str] = []

        if repo["score_breakdown"]["star_velocity_7d"] >= 25:
            reasons.append("近期 Star 增速快")
        if repo["score_breakdown"]["topic_match"] >= 8:
            reasons.append("命中核心 AI/Agent 标签")
        if repo["score_breakdown"]["keyword_match"] >= 8:
            reasons.append("描述含易用/变现关键词")
        if repo["score_breakdown"]["recent_update"] >= 10:
            reasons.append("近期仍在迭代")
        if repo.get("bonus", 0) >= 10:
            reasons.append("新兴项目/爆发力强")
        if repo["forks"] >= 100:
            reasons.append("Fork 数较高，开发者关注")

        if not reasons:
            reasons.append("综合指标入选")

        return "；".join(reasons)
