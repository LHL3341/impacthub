"""Advisor (导师推荐) API: schools, colleges, advisors directory."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models import AdvisorSchool, AdvisorCollege, Advisor
from app.services import advisor_crawler_service

router = APIRouter()


# ─────── Schemas ───────

class SchoolBrief(BaseModel):
    id: int
    name: str
    short_name: str
    english_name: str
    city: str
    province: str
    school_type: str
    is_985: bool
    is_211: bool
    is_double_first_class: bool
    homepage_url: str
    college_count: int
    advisor_count: int

    model_config = {"from_attributes": True}


class CollegeBrief(BaseModel):
    id: int
    school_id: int
    name: str
    discipline_category: str
    homepage_url: str
    advisor_count: int

    model_config = {"from_attributes": True}


class AdvisorBrief(BaseModel):
    id: int
    school_id: int
    college_id: int
    name: str
    title: str
    is_doctoral_supervisor: bool
    research_areas: list[str] | None
    homepage_url: str
    photo_url: str
    h_index: int
    citation_count: int

    model_config = {"from_attributes": True}


class SchoolDirectoryStats(BaseModel):
    total_schools: int
    schools_985: int
    schools_211: int
    total_colleges: int
    total_advisors: int
    by_province: dict[str, int]
    by_school_type: dict[str, int]


# ─────── Endpoints ───────

@router.get("/advisor/stats", response_model=SchoolDirectoryStats)
async def get_directory_stats(db: AsyncSession = Depends(get_db)):
    schools = (await db.execute(select(AdvisorSchool))).scalars().all()
    college_count = (await db.execute(select(func.count(AdvisorCollege.id)))).scalar() or 0
    advisor_count = (await db.execute(select(func.count(Advisor.id)))).scalar() or 0

    by_province: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for s in schools:
        if s.province:
            by_province[s.province] = by_province.get(s.province, 0) + 1
        if s.school_type:
            by_type[s.school_type] = by_type.get(s.school_type, 0) + 1

    return SchoolDirectoryStats(
        total_schools=len(schools),
        schools_985=sum(1 for s in schools if s.is_985),
        schools_211=sum(1 for s in schools if s.is_211),
        total_colleges=college_count,
        total_advisors=advisor_count,
        by_province=by_province,
        by_school_type=by_type,
    )


@router.get("/advisor/schools", response_model=list[SchoolBrief])
async def list_schools(
    province: str | None = None,
    school_type: str | None = None,
    tier: str | None = Query(None, description="985 / 211"),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AdvisorSchool)
    if province:
        stmt = stmt.where(AdvisorSchool.province == province)
    if school_type:
        stmt = stmt.where(AdvisorSchool.school_type == school_type)
    if tier == "985":
        stmt = stmt.where(AdvisorSchool.is_985 == True)  # noqa: E712
    elif tier == "211":
        stmt = stmt.where(AdvisorSchool.is_211 == True)  # noqa: E712
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            AdvisorSchool.name.like(like),
            AdvisorSchool.short_name.like(like),
            AdvisorSchool.english_name.like(like),
            AdvisorSchool.city.like(like),
        ))
    schools = (await db.execute(stmt)).scalars().all()

    # Compute college / advisor counts in batch
    sids = [s.id for s in schools]
    college_counts: dict[int, int] = {}
    if sids:
        rows = (await db.execute(
            select(AdvisorCollege.school_id, func.count(AdvisorCollege.id))
            .where(AdvisorCollege.school_id.in_(sids))
            .group_by(AdvisorCollege.school_id)
        )).all()
        college_counts = {sid: int(c) for sid, c in rows}
    # advisor_count is denormalized on AdvisorSchool

    out = []
    for s in schools:
        out.append(SchoolBrief(
            id=s.id, name=s.name, short_name=s.short_name, english_name=s.english_name,
            city=s.city, province=s.province, school_type=s.school_type,
            is_985=s.is_985, is_211=s.is_211, is_double_first_class=s.is_double_first_class,
            homepage_url=s.homepage_url,
            college_count=college_counts.get(s.id, 0),
            advisor_count=s.advisor_count or 0,
        ))
    # Sort: 985 first, then by advisor_count desc, then by name
    out.sort(key=lambda x: (not x.is_985, -x.advisor_count, x.name))
    return out


@router.get("/advisor/schools/{school_id}")
async def get_school(school_id: int, db: AsyncSession = Depends(get_db)):
    school = await db.get(AdvisorSchool, school_id)
    if not school:
        raise HTTPException(404, "School not found")
    colleges = (await db.execute(
        select(AdvisorCollege).where(AdvisorCollege.school_id == school_id)
    )).scalars().all()
    return {
        "school": SchoolBrief(
            id=school.id, name=school.name, short_name=school.short_name,
            english_name=school.english_name, city=school.city, province=school.province,
            school_type=school.school_type,
            is_985=school.is_985, is_211=school.is_211,
            is_double_first_class=school.is_double_first_class,
            homepage_url=school.homepage_url,
            college_count=len(colleges),
            advisor_count=school.advisor_count or 0,
        ),
        "colleges_crawled_at": school.colleges_crawled_at.isoformat() if school.colleges_crawled_at else None,
        "advisors_crawled_at": school.advisors_crawled_at.isoformat() if school.advisors_crawled_at else None,
        "colleges": [
            CollegeBrief(
                id=c.id, school_id=c.school_id, name=c.name,
                discipline_category=c.discipline_category, homepage_url=c.homepage_url,
                advisor_count=c.advisor_count or 0,
            )
            for c in colleges
        ],
    }


@router.post("/advisor/schools/{school_id}/crawl")
async def crawl_school(
    school_id: int,
    background_tasks: BackgroundTasks,
    fetch_advisors: bool = Query(False, description="If true, also crawl advisor stubs per college"),
    db: AsyncSession = Depends(get_db),
):
    school = await db.get(AdvisorSchool, school_id)
    if not school:
        raise HTTPException(404, "School not found")
    background_tasks.add_task(_do_crawl_school, school_id, fetch_advisors)
    return {"status": "crawling", "school_id": school_id, "fetch_advisors": fetch_advisors}


async def _do_crawl_school(school_id: int, fetch_advisors: bool):
    async with async_session() as db:
        school = await db.get(AdvisorSchool, school_id)
        if not school:
            return
        result = await advisor_crawler_service.crawl_school_colleges(
            db, school, fetch_advisors=fetch_advisors,
        )
        await db.commit()
        import logging
        logging.getLogger(__name__).info("Crawl school %s done: %s", school.name, result)


@router.post("/advisor/colleges/{college_id}/crawl-advisors")
async def crawl_college(
    college_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    college = await db.get(AdvisorCollege, college_id)
    if not college:
        raise HTTPException(404, "College not found")
    background_tasks.add_task(_do_crawl_college, college_id)
    return {"status": "crawling", "college_id": college_id}


async def _do_crawl_college(college_id: int):
    async with async_session() as db:
        college = await db.get(AdvisorCollege, college_id)
        if not college:
            return
        await advisor_crawler_service.crawl_college_advisors(db, college)
        await db.commit()


@router.get("/advisor/colleges/{college_id}/advisors", response_model=list[AdvisorBrief])
async def list_advisors_in_college(college_id: int, db: AsyncSession = Depends(get_db)):
    advisors = (await db.execute(
        select(Advisor).where(Advisor.college_id == college_id)
    )).scalars().all()
    return [
        AdvisorBrief(
            id=a.id, school_id=a.school_id, college_id=a.college_id,
            name=a.name, title=a.title,
            is_doctoral_supervisor=a.is_doctoral_supervisor,
            research_areas=a.research_areas,
            homepage_url=a.homepage_url, photo_url=a.photo_url,
            h_index=a.h_index, citation_count=a.citation_count,
        )
        for a in advisors
    ]
