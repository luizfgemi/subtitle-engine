"""Small domain result types shared by HTTP and background entrypoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PipelineStatus = Literal[
    "extracted_and_translated",
    "whisper_transcribed_and_translated",
    "already_exists",
    "failed",
    "ignored",
    "cancelled",
]


@dataclass
class PipelineResult:
    video_path: Path
    output_srt: Path | None
    status: PipelineStatus
    source_method: str
    details: str = ""


@dataclass
class BatchResult:
    status: Literal["completed", "error", "cancelled"]
    total_missing_found: int = 0
    results: list[PipelineResult] = field(default_factory=list)
    message: str = ""


@dataclass
class GuardianResult:
    status: Literal["completed", "error"]
    orphan_candidates: int = 0
    deleted_count: int = 0
    bad_sync_detected: int = 0
    details: str = ""
