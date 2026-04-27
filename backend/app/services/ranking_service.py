"""Ranking service: compute leaderboards across various dimensions.

Dimensions:
- total:     all visible users, ranked by selected metric
- young:     users whose first paper is within last 10 years
- direction: filter by research_direction (llm / cv / vlm / systems / theory / rl)

Metrics: h_index (default), total_citations, ccf_a_count, total_stars

Display rule: top N (default 10000) shown with exact rank, beyond that only
percentile is returned (降低 over-quantification 压力).
"""

import logging
from datetime import datetime
from typing import Literal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Paper, GithubRepo, ResearcherPersona
from app.utils.paper_dedup import deduplicate_papers

logger = logging.getLogger(__name__)

# Any user ranked beyond this position gets percentile-only display
EXACT_RANK_CUTOFF = 10000
YOUNG_YEARS = 10   # first paper within this many years = "young"

MetricKey = Literal["h_index", "total_citations", "ccf_a_count", "total_stars"]
RankingType = Literal["total", "young", "direction"]

DIRECTIONS = {"llm", "cv", "vlm", "systems", "theory", "rl"}


async def _compute_user_metrics(db: AsyncSession, user_ids: list[int]) -> dict[int, dict]:
    """Compute all metrics for a batch of users in a single pass."""
    if not user_ids:
        return {}

    # Papers grouped by user
    papers_rows = (await db.execute(
        select(Paper).where(Paper.user_id.in_(user_ids))
    )).scalars().all()

    by_user: dict[int, list] = {}
    for p in papers_rows:
        by_user.setdefault(p.user_id, []).append(p)

    # Repo stars per user
    stars_rows = (await db.execute(
        select(GithubRepo.user_id, func.coalesce(func.sum(GithubRepo.stars), 0))
        .where(GithubRepo.user_id.in_(user_ids))
        .group_by(GithubRepo.user_id)
    )).all()
    stars_by_user = {uid: int(total) for uid, total in stars_rows}

    metrics: dict[int, dict] = {}
    for uid in user_ids:
        papers_raw = by_user.get(uid, [])
        papers = deduplicate_papers(papers_raw)
        citations = [p.citation_count or 0 for p in papers]
        citations_sorted = sorted(citations, reverse=True)

        # h-index
        h = 0
        for i, c in enumerate(citations_sorted):
            if c >= i + 1:
                h = i + 1
            else:
                break

        # First paper year (for "young" classification)
        years = [p.year for p in papers if p.year and p.year > 0]
        first_year = min(years) if years else None

        metrics[uid] = {
            "h_index": h,
            "total_citations": sum(citations),
            "paper_count": len(papers),
            "ccf_a_count": sum(1 for p in papers if (p.ccf_rank or "") == "A"),
            "ccf_b_count": sum(1 for p in papers if (p.ccf_rank or "") == "B"),
            "total_stars": stars_by_user.get(uid, 0),
            "first_paper_year": first_year,
        }
    return metrics


async def compute_leaderboard(
    db: AsyncSession,
    ranking_type: RankingType = "total",
    direction: str | None = None,
    metric: MetricKey = "h_index",
    offset: int = 0,
    limit: int = 50,
    target_user_id: int | None = None,
) -> dict:
    """Compute a paginated leaderboard slice.

    Returns:
        {
            "type": "total",
            "metric": "h_index",
            "direction": None,
            "total_count": 87,
            "entries": [
                {"rank": 1, "user": {...}, "metrics": {...}, "persona_code": "DBES"},
                ...
            ],
            "target_rank": {"rank": 42, "percentile": None, "metric_value": ...}   # optional
        }
    """
    # Base query: visible users
    stmt = select(User).where(User.visible == True)  # noqa: E712

    if ranking_type == "direction":
        if not direction or direction not in DIRECTIONS:
            direction = "llm"
        stmt = stmt.where(User.research_direction == direction)

    all_users = (await db.execute(stmt)).scalars().all()
    if not all_users:
        return {
            "type": ranking_type,
            "metric": metric,
            "direction": direction,
            "total_count": 0,
            "entries": [],
        }

    user_ids = [u.id for u in all_users]
    metrics_map = await _compute_user_metrics(db, user_ids)

    # For "young": filter to users whose first paper is recent enough
    if ranking_type == "young":
        current_year = datetime.utcnow().year
        cutoff = current_year - YOUNG_YEARS
        user_ids = [
            uid for uid in user_ids
            if (metrics_map[uid]["first_paper_year"] or 0) >= cutoff
        ]

    # Sort by metric, descending
    sort_key = lambda uid: metrics_map[uid].get(metric, 0) or 0
    sorted_uids = sorted(user_ids, key=sort_key, reverse=True)

    total_count = len(sorted_uids)
    user_by_id = {u.id: u for u in all_users}

    # Load personas in one query
    persona_rows = (await db.execute(
        select(ResearcherPersona).where(ResearcherPersona.user_id.in_(sorted_uids))
    )).scalars().all()
    persona_by_uid = {p.user_id: p.persona_code for p in persona_rows}

    # Find target user rank if requested
    target_info = None
    if target_user_id and target_user_id in metrics_map:
        try:
            target_rank = sorted_uids.index(target_user_id) + 1
        except ValueError:
            target_rank = None
        if target_rank:
            if target_rank <= EXACT_RANK_CUTOFF:
                target_info = {
                    "rank": target_rank,
                    "percentile": None,
                    "metric_value": metrics_map[target_user_id].get(metric, 0),
                }
            else:
                pct = (target_rank / total_count) * 100
                target_info = {
                    "rank": None,
                    "percentile": round(100 - pct, 1),   # "top X% of total"
                    "metric_value": metrics_map[target_user_id].get(metric, 0),
                }

    # Paginate
    page = sorted_uids[offset : offset + limit]

    entries = []
    for i, uid in enumerate(page):
        absolute_rank = offset + i + 1
        user = user_by_id[uid]
        m = metrics_map[uid]
        display = {}
        if absolute_rank <= EXACT_RANK_CUTOFF:
            display["rank"] = absolute_rank
            display["percentile"] = None
        else:
            pct = (absolute_rank / total_count) * 100
            display["rank"] = None
            display["percentile"] = round(100 - pct, 1)
        entries.append({
            **display,
            "user": {
                "id": user.id,
                "name": user.name or user.github_username,
                "avatar_url": user.avatar_url,
                "scholar_id": user.scholar_id,
                "github_username": user.github_username,
                "research_direction": user.research_direction or None,
                "seed_tier": user.seed_tier or None,
                "honor_tags": user.honor_tags or [],
            },
            "metrics": {
                "h_index": m["h_index"],
                "total_citations": m["total_citations"],
                "paper_count": m["paper_count"],
                "ccf_a_count": m["ccf_a_count"],
                "total_stars": m["total_stars"],
                "first_paper_year": m["first_paper_year"],
            },
            "persona_code": persona_by_uid.get(uid),
        })

    return {
        "type": ranking_type,
        "metric": metric,
        "direction": direction if ranking_type == "direction" else None,
        "total_count": total_count,
        "entries": entries,
        "target_rank": target_info,
    }
