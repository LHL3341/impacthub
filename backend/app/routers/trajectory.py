"""Research trajectory API endpoints."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, ResearchTrajectory
from app.services import trajectory_service
from app.deps import resolve_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/trajectory/{identifier}")
async def get_trajectory(
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(ResearchTrajectory).where(ResearchTrajectory.user_id == user.id)
    )).scalars().first()
    if not row:
        return None
    data = dict(row.trajectory_json) if isinstance(row.trajectory_json, dict) else {}
    data["refreshed_at"] = row.refreshed_at.isoformat() if row.refreshed_at else None
    return data


@router.post("/trajectory/{identifier}/refresh")
async def refresh_trajectory(
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh trajectory — pure computation, returns immediately."""
    try:
        result = await trajectory_service.refresh_trajectory(db, user)
        await db.commit()
        if not result:
            return {"status": "skipped", "reason": "insufficient papers"}
        # Return the data directly so frontend doesn't need to poll
        data = dict(result.trajectory_json) if isinstance(result.trajectory_json, dict) else {}
        data["refreshed_at"] = result.refreshed_at.isoformat() if result.refreshed_at else None
        return {"status": "done", "data": data}
    except Exception:
        logger.exception("Trajectory refresh failed for user %d", user.id)
        return {"status": "error"}
