"""Researcher persona API endpoints."""

import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, ResearcherPersona
from app.services import persona_service
from app.services.persona_service import PERSONAS
from app.deps import resolve_user
from app.schemas import PersonaOut

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/persona/{identifier}")
async def get_persona(
    user: User = Depends(resolve_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(ResearcherPersona).where(ResearcherPersona.user_id == user.id)
    )).scalars().first()
    if not row or not row.persona_code:
        return None

    code = row.persona_code
    persona_def = PERSONAS.get(code, PERSONAS.get("PT__", {}))

    return {
        "user_id": row.user_id,
        "persona_code": code,
        "name_zh": persona_def.get("name_zh", ""),
        "name_en": persona_def.get("name_en", ""),
        "emoji": persona_def.get("emoji", ""),
        "tagline": persona_def.get("tagline", ""),
        "description": persona_def.get("description", ""),
        "traits": persona_def.get("traits", []),
        "color_from": persona_def.get("color_from", "#6366f1"),
        "color_to": persona_def.get("color_to", "#8b5cf6"),
        "dimension_scores": row.dimension_scores if isinstance(row.dimension_scores, dict) else {},
        "raw_metrics": row.raw_metrics if isinstance(row.raw_metrics, dict) else {},
        "refreshed_at": row.refreshed_at.isoformat() if row.refreshed_at else None,
    }


@router.post("/persona/{identifier}/refresh")
async def refresh_persona(
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
            await persona_service.compute_persona(db, user)
            await db.commit()
    except Exception:
        logger.exception("Persona refresh failed for user %d", user_id)
