"""Select and process media that Bazarr reports as missing subtitles."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

from app import config
from app.models import BatchResult
from app.pipeline import process_video_subtitles
from app.satisfaction import is_embedded_satisfied

LOGGER = logging.getLogger("subtitle-engine.batch")
StopRequested = Callable[[], bool]


def process_missing(
    limit: int = 10,
    target_language: str = "pt-BR",
    stop_requested: StopRequested | None = None,
) -> BatchResult:
    if not config.BAZARR_DATABASE_PATH.is_file():
        return BatchResult(
            status="error",
            message=f"Bazarr DB not found at {config.BAZARR_DATABASE_PATH}",
        )

    try:
        with sqlite3.connect(
            f"file:{config.BAZARR_DATABASE_PATH}?mode=ro", uri=True
        ) as connection:
            rows = connection.execute(
                "SELECT path FROM table_movies WHERE missing_subtitles LIKE '%pb%' OR missing_subtitles LIKE '%pt-BR%' "
                "UNION ALL "
                "SELECT path FROM table_episodes WHERE missing_subtitles LIKE '%pb%' OR missing_subtitles LIKE '%pt-BR%'"
            ).fetchall()
    except sqlite3.Error as err:
        LOGGER.error("Failed to query Bazarr DB: %s", err)
        return BatchResult(status="error", message=str(err))

    candidates: list[Path] = []
    for (raw_path,) in rows:
        if stop_requested and stop_requested():
            return BatchResult(status="cancelled", message="Batch cancelled")
        video = Path(raw_path)
        target = video.with_name(f"{video.stem}.{target_language}.srt")
        if (
            video.is_file()
            and not target.is_file()
            and not is_embedded_satisfied(video, target_language)
        ):
            candidates.append(video)

    results = []
    for video in candidates[:limit]:
        if stop_requested and stop_requested():
            break
        result = process_video_subtitles(video, target_language, stop_requested)
        results.append(result)
        if result.status == "cancelled":
            break

    cancelled = bool(stop_requested and stop_requested())
    status = "cancelled" if cancelled else "completed"
    message = (
        f"Batch cancelled after {len(results)} items"
        if cancelled
        else f"Processed {len(results)} truly missing items out of {len(candidates)} candidates."
    )
    return BatchResult(status, len(candidates), results, message)
