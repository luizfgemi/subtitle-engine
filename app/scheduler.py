"""Async background task scheduler for subtitle-engine.

Executes periodic batch-missing generation and guardian orphan audit tasks
based on environment configuration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from app.guardian import run_guardian_audit

LOGGER = logging.getLogger("subtitle-engine.scheduler")

# --- Scheduler configuration ---
BATCH_MISSING_INTERVAL_MINUTES: int = int(os.getenv("SCHEDULE_BATCH_MISSING_INTERVAL_MINUTES", "30"))
GUARDIAN_INTERVAL_HOURS: int = int(os.getenv("SCHEDULE_GUARDIAN_INTERVAL_HOURS", "6"))
SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("true", "1", "yes")

_scheduler_tasks: list[asyncio.Task] = []


async def _batch_missing_loop():
    """Periodic background loop for batch-missing subtitle generation."""
    # Delay initial run by 60 seconds to allow application startup
    await asyncio.sleep(60)
    interval_seconds = BATCH_MISSING_INTERVAL_MINUTES * 60

    while True:
        try:
            LOGGER.info("Starting scheduled batch-missing check...")
            # Import dynamically to prevent circular dependencies
            from app.api import process_batch_missing
            from app.schemas import BatchMissingRequest

            req = BatchMissingRequest(limit=10)
            res = await asyncio.to_thread(process_batch_missing, req)
            LOGGER.info("Scheduled batch-missing finished: %s", res.message)
        except Exception as err:
            LOGGER.error("Error in scheduled batch-missing task: %s", err)

        await asyncio.sleep(interval_seconds)


async def _guardian_audit_loop():
    """Periodic background loop for guardian orphan audit and cleanup."""
    await asyncio.sleep(120)
    interval_seconds = GUARDIAN_INTERVAL_HOURS * 3600

    while True:
        try:
            LOGGER.info("Starting scheduled Guardian audit...")
            res = await asyncio.to_thread(run_guardian_audit, True)
            LOGGER.info("Scheduled Guardian audit finished: %s", res.details)
        except Exception as err:
            LOGGER.error("Error in scheduled Guardian audit task: %s", err)

        await asyncio.sleep(interval_seconds)


def start_scheduler():
    """Start background scheduler tasks upon FastAPI startup."""
    if not SCHEDULER_ENABLED:
        LOGGER.info("Background scheduler is disabled via SCHEDULER_ENABLED=false")
        return

    LOGGER.info(
        "Starting background scheduler (batch_missing every %dm, guardian every %dh)...",
        BATCH_MISSING_INTERVAL_MINUTES,
        GUARDIAN_INTERVAL_HOURS,
    )
    t1 = asyncio.create_task(_batch_missing_loop())
    t2 = asyncio.create_task(_guardian_audit_loop())
    _scheduler_tasks.extend([t1, t2])


def stop_scheduler():
    """Cancel all active background scheduler tasks upon FastAPI shutdown."""
    for task in _scheduler_tasks:
        if not task.done():
            task.cancel()
    _scheduler_tasks.clear()
    LOGGER.info("Background scheduler stopped.")
