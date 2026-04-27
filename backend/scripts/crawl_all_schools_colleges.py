"""Batch crawler for stage 2a: college lists across all 147 schools.

Skips schools already crawled. Logs to /tmp/advisor_crawl.log so the cron loop
can monitor progress.

Usage:
    cd backend && python scripts/crawl_all_schools_colleges.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import async_session
from app.models import AdvisorSchool, AdvisorCollege
from app.services import advisor_crawler_service

LOG_PATH = Path("/tmp/advisor_crawl_colleges.log")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


async def main():
    setup_logging()
    log = logging.getLogger(__name__)

    # Load all schools that haven't been crawled yet
    async with async_session() as db:
        schools = (await db.execute(
            select(AdvisorSchool).where(
                AdvisorSchool.homepage_url != "",
                AdvisorSchool.colleges_crawled_at.is_(None),
            ).order_by(AdvisorSchool.is_985.desc(), AdvisorSchool.is_211.desc())
        )).scalars().all()

    total = len(schools)
    log.info("Starting batch crawl: %d schools to process", total)
    if not total:
        log.info("Nothing to do. All schools already crawled.")
        return

    successes = 0
    failures: list[tuple[str, list[str]]] = []
    skipped: list[str] = []
    t0 = time.time()

    for i, s in enumerate(schools, 1):
        elapsed = time.time() - t0
        log.info(
            "[%3d/%3d] %-20s (%s) | elapsed %.0fs",
            i, total, s.name, s.homepage_url, elapsed,
        )
        try:
            async with async_session() as db:
                school = await db.get(AdvisorSchool, s.id)
                result = await advisor_crawler_service.crawl_school_colleges(
                    db, school, fetch_advisors=False,
                )
                await db.commit()
                if result["colleges_added"] == 0:
                    failures.append((s.name, result.get("errors", [])))
                    log.warning("  → 0 colleges added: %s", result.get("errors"))
                else:
                    successes += 1
                    log.info(
                        "  → +%d colleges (%s errors)",
                        result["colleges_added"], len(result.get("errors", [])),
                    )
        except Exception as e:
            log.exception("  → CRASHED: %s", e)
            failures.append((s.name, [str(e)]))

    elapsed = time.time() - t0
    log.info(
        "DONE in %.0fs. success=%d failure=%d skipped=%d",
        elapsed, successes, len(failures), len(skipped),
    )
    if failures:
        log.info("Failures:")
        for name, errs in failures[:30]:
            log.info("  %s: %s", name, errs)


if __name__ == "__main__":
    asyncio.run(main())
