"""Capability portrait API endpoints."""

import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, CapabilityProfile
from app.services import capability_service
from app.deps import resolve_user

logger = logging.getLogger(__name__)
router = APIRouter()


ROLE_META = {
    "originator":     {"zh": "开创者",   "en": "Originator",    "emoji": "🌱", "color": "#6366f1"},
    "early_adopter":  {"zh": "早期采用者", "en": "Early Adopter", "emoji": "⚡", "color": "#0ea5e9"},
    "extender":       {"zh": "扩展者",   "en": "Extender",      "emoji": "🛠️", "color": "#10b981"},
    "follower":       {"zh": "跟随者",   "en": "Follower",      "emoji": "🚶", "color": "#94a3b8"},
}


def _decorate_profile(p: dict) -> dict:
    meta = ROLE_META.get(p.get("role", ""), {})
    return {
        **p,
        "role_zh": meta.get("zh", p.get("role", "")),
        "role_en": meta.get("en", p.get("role", "")),
        "role_emoji": meta.get("emoji", ""),
        "role_color": meta.get("color", "#6366f1"),
    }


@router.get("/capability/{identifier}")
async def get_capability(
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(CapabilityProfile).where(CapabilityProfile.user_id == user.id)
    )).scalars().first()
    if not row or not (row.profiles_json or []):
        return None

    profiles_raw = row.profiles_json if isinstance(row.profiles_json, list) else []
    profiles = [_decorate_profile(p) for p in profiles_raw if isinstance(p, dict)]

    primary_meta = ROLE_META.get(row.primary_role, {})
    return {
        "user_id": row.user_id,
        "primary_role": row.primary_role,
        "primary_role_zh": primary_meta.get("zh", row.primary_role),
        "primary_role_emoji": primary_meta.get("emoji", ""),
        "primary_role_color": primary_meta.get("color", "#6366f1"),
        "primary_direction": row.primary_direction or "",
        "profiles": profiles,
        "rationale": row.rationale or "",
        "refreshed_at": row.refreshed_at.isoformat() if row.refreshed_at else None,
    }


@router.post("/capability/{identifier}/refresh")
async def refresh_capability(
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
            await capability_service.refresh_capability(db, user)
            await db.commit()
    except Exception:
        logger.exception("Capability refresh failed for user %d", user_id)
