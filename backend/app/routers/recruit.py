"""B2B recruiter talent search endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import recruit_service

router = APIRouter()


class RecruitSearchRequest(BaseModel):
    jd: str = Field(..., min_length=1, max_length=4000, description="Job description / talent requirements (free text)")
    top_k: int = Field(10, ge=1, le=20)


@router.post("/recruit/search")
async def search(
    req: RecruitSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    return await recruit_service.search_talent(db, req.jd, top_k=req.top_k)
