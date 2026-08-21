"""FastAPI router and endpoints for subtitle-engine."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from contextlib import asynccontextmanager
from app import config
from app.guardian import run_guardian_audit
from app.pipeline import process_video_subtitles
from app.probe import probe_media
from app.scheduler import start_scheduler, stop_scheduler
from app.schemas import (
    AudioTrackInfo,
    BatchMissingRequest,
    BatchMissingResponse,
    GenerateRequest,
    GuardianAuditResponse,
    HealthResponse,
    PipelineResultResponse,
    ProbeRequest,
    ProbeResponse,
    SubtitleTrackInfo,
)

LOGGER = logging.getLogger("subtitle-engine.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle events."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Subtitle Engine",
    description="Subtitle generation, extraction, translation and guardian microservice",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return runtime service health and Whisper GPU configuration."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        whisper_model=config.WHISPER_MODEL,
        whisper_device=config.WHISPER_DEVICE,
    )


@app.post("/api/v1/probe", response_model=ProbeResponse)
def probe_file(req: ProbeRequest) -> ProbeResponse:
    """Inspect media file streams using ffprobe."""
    try:
        result = probe_media(Path(req.path))
        return ProbeResponse(
            path=str(result.path),
            duration_seconds=result.duration_seconds,
            audio_tracks=[
                AudioTrackInfo(
                    index=t.index,
                    codec=t.codec_name,
                    language=t.language,
                    channels=2,
                )
                for t in result.audio_tracks
            ],
            subtitle_tracks=[
                SubtitleTrackInfo(
                    index=t.index,
                    codec=t.codec_name,
                    language=t.language,
                    title=t.title,
                )
                for t in result.subtitle_tracks
            ],
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@app.post("/api/v1/generate", response_model=PipelineResultResponse)
def generate_subtitle(req: GenerateRequest) -> PipelineResultResponse:
    """Process a single video file to extract, translate, or transcribe subtitles."""
    video_path = Path(req.path)
    res = process_video_subtitles(video_path, req.target_language)

    return PipelineResultResponse(
        video_path=str(res.video_path),
        output_srt=str(res.output_srt) if res.output_srt else None,
        status=res.status,
        source_method=res.source_method,
        details=res.details,
    )


def _extract_video_path_from_payload(payload: dict[str, Any]) -> str | None:
    """Extract video file path from raw webhook payload (Bazarr, Radarr, Sonarr, or direct path).

    Args:

        payload: Raw JSON webhook payload dictionary.

    Returns:
        Absolute video file path string if present, else None.
    """
    if "path" in payload and isinstance(payload["path"], str):
        return payload["path"]

    if "episode" in payload and isinstance(payload["episode"], dict):
        if "path" in payload["episode"]:
            return payload["episode"]["path"]
    if "movie" in payload and isinstance(payload["movie"], dict):
        if "path" in payload["movie"]:
            return payload["movie"]["path"]
        if "folderPath" in payload["movie"]:
            return payload["movie"]["folderPath"]

    if "episodeFile" in payload and isinstance(payload["episodeFile"], dict):
        if "path" in payload["episodeFile"]:
            return payload["episodeFile"]["path"]

    return None


@app.post("/api/v1/event", response_model=PipelineResultResponse)
def handle_bazarr_event(payload: dict[str, Any]) -> PipelineResultResponse:
    """Handle incoming Bazarr/Radarr/Sonarr webhook events."""
    video_path_str = _extract_video_path_from_payload(payload)
    if not video_path_str:
        LOGGER.info("Received event payload without valid media file path: %s", payload)
        return PipelineResultResponse(
            video_path="",
            output_srt=None,
            status="ignored",
            source_method="",
            details="Payload does not contain a valid media file path (test or non-media event)",
        )

    target_language = payload.get("target_language", "pt-BR")
    video_path = Path(video_path_str)
    res = process_video_subtitles(video_path, target_language)

    return PipelineResultResponse(
        video_path=str(res.video_path),
        output_srt=str(res.output_srt) if res.output_srt else None,
        status=res.status,
        source_method=res.source_method,
        details=res.details,
    )


@app.post("/api/v1/batch-missing", response_model=BatchMissingResponse)
def process_batch_missing(req: BatchMissingRequest) -> BatchMissingResponse:
    """Query Bazarr DB for missing pt-BR subtitles and process them in batch."""
    bazarr_db_path = config.BAZARR_DATABASE_PATH
    if not bazarr_db_path.is_file():
        return BatchMissingResponse(
            status="error",
            message=f"Bazarr DB not found at {bazarr_db_path}",
            total_missing_found=0,
            processed_count=0,
            results=[],
        )

    missing_paths: list[Path] = []
    try:
        conn = sqlite3.connect(f"file:{bazarr_db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        query = (
            "SELECT path FROM table_movies WHERE missing_subtitles LIKE '%pb%' OR missing_subtitles LIKE '%pt-BR%' "
            "UNION ALL "
            "SELECT path FROM table_episodes WHERE missing_subtitles LIKE '%pb%' OR missing_subtitles LIKE '%pt-BR%'"
        )

        rows = conn.execute(query).fetchall()
        for row in rows:
            p = Path(row["path"])
            if p.is_file():
                # Filter out files that already have target subtitle on disk
                target_srt = p.with_name(f"{p.stem}.{req.target_language}.srt")
                if not target_srt.is_file():
                    missing_paths.append(p)

        conn.close()
    except Exception as err:
        LOGGER.error("Failed to query Bazarr DB: %s", err)
        return BatchMissingResponse(
            status="error",
            message=str(err),
            total_missing_found=0,
            processed_count=0,
            results=[],
        )

    selected = missing_paths[: req.limit]
    results: list[PipelineResultResponse] = []

    for video_path in selected:
        res = process_video_subtitles(video_path, req.target_language)
        results.append(
            PipelineResultResponse(
                video_path=str(res.video_path),
                output_srt=str(res.output_srt) if res.output_srt else None,
                status=res.status,
                source_method=res.source_method,
                details=res.details,
            )
        )

    return BatchMissingResponse(
        status="completed",
        total_missing_found=len(missing_paths),
        processed_count=len(results),
        results=results,
        message=f"Processed {len(results)} truly missing items out of {len(missing_paths)} candidates.",
    )


@app.post("/api/v1/guardian/audit", response_model=GuardianAuditResponse)
def trigger_guardian_audit(apply_cleanup: bool = False) -> GuardianAuditResponse:
    """Trigger manual Guardian audit for orphan subtitle cleanup and sync validation."""
    return run_guardian_audit(apply_cleanup=apply_cleanup)


