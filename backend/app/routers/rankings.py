"""Leaderboard / rankings API."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.ranking_service import compute_leaderboard, DIRECTIONS

router = APIRouter()


@router.get("/rankings")
async def get_rankings(
    type: Literal["total", "young", "direction"] = "total",
    direction: str | None = None,
    metric: Literal["h_index", "total_citations", "ccf_a_count", "total_stars"] = "h_index",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    target_user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    if direction and direction not in DIRECTIONS:
        direction = None
    result = await compute_leaderboard(
        db,
        ranking_type=type,
        direction=direction,
        metric=metric,
        offset=offset,
        limit=limit,
        target_user_id=target_user_id,
    )
    return result


@router.get("/rankings/directions")
async def list_directions():
    return sorted(list(DIRECTIONS))
