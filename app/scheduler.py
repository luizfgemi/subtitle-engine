"""Async background task scheduler for subtitle-engine.

Executes periodic batch-missing generation and guardian orphan audit tasks
based on environment configuration.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

from app import config
from app.batch import process_missing
from app.guardian import run_guardian_audit

LOGGER = logging.getLogger("subtitle-engine.scheduler")

_scheduler_tasks: list[asyncio.Task] = []
_stop_event = threading.Event()


async def _run_daemon(function: Callable[..., Any], *args: Any) -> Any:
    """Run blocking work without making its thread prevent process shutdown."""
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def run() -> None:
        try:
            result = function(*args)
        except BaseException as err:
            loop.call_soon_threadsafe(_finish, None, err)
        else:
            loop.call_soon_threadsafe(_finish, result, None)

    def _finish(result: Any, error: BaseException | None) -> None:
        if future.done():
            return
        if error:
            future.set_exception(error)
        else:
            future.set_result(result)

    threading.Thread(target=run, daemon=True).start()
    return await future


async def _batch_missing_loop():
    """Periodic background loop for batch-missing subtitle generation."""
    # Delay initial run by 60 seconds to allow application startup
    await asyncio.sleep(60)
    interval_seconds = config.BATCH_MISSING_INTERVAL_MINUTES * 60

    while True:
        try:
            LOGGER.info("Starting scheduled batch-missing check...")
            res = await _run_daemon(process_missing, 10, "pt-BR", _stop_event.is_set)
            LOGGER.info("Scheduled batch-missing finished: %s", res.message)
        except Exception as err:
            LOGGER.error("Error in scheduled batch-missing task: %s", err)

        await asyncio.sleep(interval_seconds)


async def _guardian_audit_loop():
    """Periodic background loop for guardian orphan audit and cleanup."""
    await asyncio.sleep(120)
    interval_seconds = config.GUARDIAN_INTERVAL_HOURS * 3600

    while True:
        try:
            LOGGER.info("Starting scheduled Guardian audit...")
            res = await _run_daemon(run_guardian_audit, True)
            LOGGER.info("Scheduled Guardian audit finished: %s", res.details)
        except Exception as err:
            LOGGER.error("Error in scheduled Guardian audit task: %s", err)

        await asyncio.sleep(interval_seconds)


def start_scheduler():
    """Start background scheduler tasks upon FastAPI startup."""
    if not config.SCHEDULER_ENABLED:
        LOGGER.info("Background scheduler is disabled via SCHEDULER_ENABLED=false")
        return

    LOGGER.info(
        "Starting background scheduler (batch_missing every %dm, guardian every %dh)...",
        config.BATCH_MISSING_INTERVAL_MINUTES,
        config.GUARDIAN_INTERVAL_HOURS,
    )
    _stop_event.clear()
    t1 = asyncio.create_task(_batch_missing_loop())
    t2 = asyncio.create_task(_guardian_audit_loop())
    _scheduler_tasks.extend([t1, t2])


async def stop_scheduler() -> None:
    """Cancel all active background scheduler tasks upon FastAPI shutdown."""
    _stop_event.set()
    for task in _scheduler_tasks:
        if not task.done():
            task.cancel()
    if _scheduler_tasks:
        await asyncio.gather(*_scheduler_tasks, return_exceptions=True)
    _scheduler_tasks.clear()
    LOGGER.info("Background scheduler stopped.")
