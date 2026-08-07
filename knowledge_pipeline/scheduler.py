"""
scheduler.py — Module 7: Background ingest scheduler.

Wraps APScheduler's BackgroundScheduler to run the ingest job every
INGEST_INTERVAL_HOURS. The job is wrapped so that ANY exception it raises is
caught and logged — a single failed cycle (e.g. Ollama down, network blip) must
never tear down the scheduler; the next cycle simply tries again.
"""

from __future__ import annotations

import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler

import config

logger = logging.getLogger(__name__)

INGEST_JOB_ID = "knowledge_ingest"


def create_scheduler(
    ingest_fn: Callable[[], object],
    interval_hours: float | None = None,
) -> BackgroundScheduler:
    """
    Build (but do not start) a BackgroundScheduler that runs ``ingest_fn`` on a
    fixed interval. The caller is responsible for ``.start()`` / ``.shutdown()``.
    """
    interval_hours = interval_hours if interval_hours is not None else config.INGEST_INTERVAL_HOURS

    scheduler = BackgroundScheduler()

    def _safe_ingest() -> None:
        """Run the ingest job, swallowing and logging any failure."""
        logger.info("Scheduled ingest starting.")
        try:
            result = ingest_fn()
            logger.info("Scheduled ingest finished (result=%s).", result)
        except Exception as exc:  # keep the scheduler alive no matter what
            logger.exception("Scheduled ingest failed and was skipped: %s", exc)

    scheduler.add_job(
        _safe_ingest,
        trigger="interval",
        hours=interval_hours,
        id=INGEST_JOB_ID,
        replace_existing=True,
        max_instances=1,   # never overlap ingest runs
        coalesce=True,     # collapse missed runs into one
    )
    logger.info("Scheduler configured: ingest every %s hour(s).", interval_hours)
    return scheduler
