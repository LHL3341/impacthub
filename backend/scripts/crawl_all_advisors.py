"""Phase 2b: crawl advisor stubs for every college that has a homepage URL.

Runs sequentially. Skips colleges already crawled (advisors_crawled_at NOT NULL).
Logs to /tmp/advisor_crawl_advisors.log.

Usage:
    cd backend && python scripts/crawl_all_advisors.py [--school-id N] [--max N]
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import AdvisorSchool, AdvisorCollege, Advisor
from app.services import advisor_crawler_service

LOG_PATH = Path("/tmp/advisor_crawl_advisors.log")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


async def update_school_count(db: AsyncSession, school_id: int):
    from sqlalchemy import func
    n = (await db.execute(
        select(func.count(Advisor.id)).where(Advisor.school_id == school_id)
    )).scalar() or 0
    from datetime import datetime
    await db.execute(
        update(AdvisorSchool).where(AdvisorSchool.id == school_id)
        .values(advisor_count=n, advisors_crawled_at=datetime.utcnow())
    )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--school-id", type=int, help="Limit to one school")
    parser.add_argument("--max", type=int, default=0, help="Stop after N colleges (0 = no limit)")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger(__name__)

    async with async_session() as db:
        stmt = select(AdvisorCollege).where(
            AdvisorCollege.homepage_url != "",
            AdvisorCollege.advisors_crawled_at.is_(None),
        ).order_by(AdvisorCollege.school_id, AdvisorCollege.id)
        if args.school_id:
            stmt = stmt.where(AdvisorCollege.school_id == args.school_id)
        colleges = (await db.execute(stmt)).scalars().all()

    total = len(colleges)
    if args.max:
        colleges = colleges[: args.max]
    log.info("Advisor crawl: %d colleges queued (cap=%s)", total, args.max or "none")
    if not colleges:
        log.info("Nothing to do.")
        return

    successes = 0
    skipped = 0
    failures = 0
    t0 = time.time()
    last_school_id = None

    for i, c in enumerate(colleges, 1):
        elapsed = time.time() - t0
        log.info(
            "[%4d/%4d] college=%s (school=%d) | elapsed %.0fs",
            i, len(colleges), c.name, c.school_id, elapsed,
        )
        try:
            async with async_session() as db:
                college = await db.get(AdvisorCollege, c.id)
                # Mark crawled regardless of result so we don't infinite-retry
                from datetime import datetime
                result = await advisor_crawler_service.crawl_college_advisors(db, college)
                college.advisors_crawled_at = datetime.utcnow()
                # If school changed since last iteration, update prior school's denorm count
                if last_school_id is not None and last_school_id != c.school_id:
                    await update_school_count(db, last_school_id)
                last_school_id = c.school_id
                await db.commit()
                added = result.get("advisors_added", 0)
                if added > 0:
                    successes += 1
                    log.info("  → +%d advisors", added)
                else:
                    skipped += 1
                    log.info("  → 0 advisors (page may not be a faculty list)")
        except Exception as e:
            failures += 1
            log.exception("  → CRASHED: %s", e)

    # Final school count update
    if last_school_id is not None:
        async with async_session() as db:
            await update_school_count(db, last_school_id)
            await db.commit()

    elapsed = time.time() - t0
    log.info(
        "DONE in %.0fs. ok=%d empty=%d crashed=%d",
        elapsed, successes, skipped, failures,
    )


if __name__ == "__main__":
    asyncio.run(main())
