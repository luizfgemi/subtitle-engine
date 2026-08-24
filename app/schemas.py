"""Domain models and Pydantic schemas for subtitle-engine.

Provides explicit, strictly-typed data transfer objects (DTOs) for API
requests, responses, media probe results, and pipeline status.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models import PipelineStatus


class HealthResponse(BaseModel):
    """API health status and Whisper runtime configuration."""

    status: str = Field(default="ok", description="Service health status")
    version: str = Field(..., description="Microservice semantic version")
    whisper_model: str = Field(..., description="Active Whisper model name")
    whisper_device: str = Field(..., description="Hardware compute device (cuda/cpu)")
    translation_model: str = Field(..., description="Active Ollama translation model")


class ProbeRequest(BaseModel):
    """Payload to inspect a media file's audio and subtitle streams."""

    path: str = Field(..., description="Absolute path to the media file")


class AudioTrackInfo(BaseModel):
    """Audio stream metadata extracted from ffprobe."""

    index: int = Field(..., description="Stream index in the container")
    codec: str = Field(..., description="Audio codec name (e.g. ac3, eac3, aac)")
    language: str = Field(default="und", description="ISO language code or und")
    channels: int = Field(default=2, description="Number of audio channels")


class SubtitleTrackInfo(BaseModel):
    """Subtitle stream metadata extracted from ffprobe."""

    index: int = Field(..., description="Stream index in the container")
    codec: str = Field(..., description="Subtitle codec name (e.g. subrip, ass)")
    language: str = Field(default="und", description="ISO language code or und")
    title: str = Field(default="", description="Track title metadata")


class ProbeResponse(BaseModel):
    """Detailed stream metadata resulting from media inspection."""

    path: str = Field(..., description="Absolute path to inspected media file")
    duration_seconds: float = Field(..., description="Media duration in seconds")
    audio_tracks: list[AudioTrackInfo] = Field(default_factory=list, description="Audio streams")
    subtitle_tracks: list[SubtitleTrackInfo] = Field(default_factory=list, description="Subtitle streams")


class GenerateRequest(BaseModel):
    """Request payload to generate or extract subtitles for a video file."""

    path: str = Field(..., description="Absolute path to the video file")
    target_language: str = Field(default="pt-BR", description="Target subtitle language code")


class PipelineResultResponse(BaseModel):
    """Outcome of subtitle processing for a single video file."""

    video_path: str = Field(..., description="Target video path")
    output_srt: str | None = Field(default=None, description="Path to generated/extracted .srt file if successful")
    status: PipelineStatus = Field(..., description="Pipeline execution outcome status")
    source_method: str = Field(..., description="Method used (e.g. embedded_pt_sub, embedded_en_sub, whisper_asr)")
    details: str = Field(default="", description="Human readable result summary or error message")


class BatchMissingRequest(BaseModel):
    """Payload to request processing of missing subtitles from Bazarr DB."""

    limit: int = Field(default=10, ge=1, le=100, description="Max missing items to process per batch")
    target_language: str = Field(default="pt-BR", description="Target subtitle language code")


class BatchMissingResponse(BaseModel):
    """Result summary of a batch processing operation."""

    status: str = Field(..., description="Batch operation status (completed/error)")
    total_missing_found: int = Field(default=0, description="Total missing items queried from Bazarr DB")
    processed_count: int = Field(default=0, description="Number of items processed in this batch")
    results: list[PipelineResultResponse] = Field(default_factory=list, description="Individual item outcomes")
    message: str = Field(default="", description="Error or diagnostic message")


class GuardianAuditResponse(BaseModel):
    """Result summary of guardian sync validation and orphan subtitle cleanup."""

    status: str = Field(..., description="Audit status (completed/error)")
    orphan_candidates: int = Field(default=0, description="Number of orphan subtitle files detected")
    deleted_count: int = Field(default=0, description="Number of orphan files purged")
    bad_sync_detected: int = Field(default=0, description="Number of bad sync entries flagged")
    details: str = Field(default="", description="Audit execution details")
