"""Annual poem (年度诗篇) API."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, AnnualPoem
from app.services import annual_poem_service
from app.deps import resolve_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _default_year() -> int:
    """Default to previous calendar year (so people see their completed year)."""
    return datetime.utcnow().year - 1


@router.get("/poem/{identifier}")
async def get_poem(
    year: int | None = Query(None),
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    if year is None:
        # Prefer most recent cached; fall back to default year if nothing
        row = (await db.execute(
            select(AnnualPoem)
            .where(AnnualPoem.user_id == user.id)
            .order_by(desc(AnnualPoem.year))
            .limit(1)
        )).scalars().first()
        if not row:
            return None
    else:
        row = (await db.execute(
            select(AnnualPoem).where(and_(AnnualPoem.user_id == user.id, AnnualPoem.year == year))
        )).scalars().first()
        if not row:
            return None

    data = row.content_json if isinstance(row.content_json, dict) else {}
    return {
        "user_id": row.user_id,
        "year": row.year,
        "title": data.get("title", ""),
        "verses": data.get("verses", []),
        "highlights": data.get("highlights", []),
        "theme": data.get("theme", "indigo"),
        "refreshed_at": row.refreshed_at.isoformat() if row.refreshed_at else None,
    }


@router.post("/poem/{identifier}/refresh")
async def refresh_poem(
    background_tasks: BackgroundTasks,
    year: int | None = Query(None),
    user: User = Depends(resolve_user),
):
    y = year if year is not None else _default_year()
    background_tasks.add_task(_do_refresh, user.id, y)
    return {"status": "refreshing", "year": y}


async def _do_refresh(user_id: int, year: int):
    from app.database import async_session
    try:
        async with async_session() as db:
            user = await db.get(User, user_id)
            if not user:
                return
            await annual_poem_service.refresh_annual_poem(db, user, year)
            await db.commit()
    except Exception:
        logger.exception("Annual poem refresh failed for user %d year %d", user_id, year)
