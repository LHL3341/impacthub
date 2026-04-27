"""Career history API."""

import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, CareerHistory
from app.services import career_service
from app.deps import resolve_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/career/{identifier}")
async def get_career(
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(CareerHistory).where(CareerHistory.user_id == user.id)
    )).scalars().first()
    if not row:
        return None
    return {
        "user_id": row.user_id,
        "timeline": row.timeline_json if isinstance(row.timeline_json, list) else [],
        "current": row.current or "",
        "sources": row.sources if isinstance(row.sources, list) else [],
        "refreshed_at": row.refreshed_at.isoformat() if row.refreshed_at else None,
    }


@router.post("/career/{identifier}/refresh")
async def refresh_career(
    background_tasks: BackgroundTasks,
    user: User = Depends(resolve_user),
):
    background_tasks.add_task(_do_refresh, user.id)
    return {"status": "refreshing"}


async def _do_refresh(user_id: int):
    from app.database import async_session
    try:
        async with async_session() as db:
            user = await db.get(User, user_id)
            if not user:
                return
            await career_service.refresh_career(db, user)
            await db.commit()
    except Exception:
        logger.exception("Career refresh failed for user %d", user_id)
