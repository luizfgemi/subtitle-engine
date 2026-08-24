"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path


# --- API ---
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8090"))

# --- Media roots ---
MOVIE_ROOT: Path = Path(os.getenv("MOVIE_ROOT", "/movies"))
SERIES_ROOT: Path = Path(os.getenv("SERIES_ROOT", "/series"))
MEDIA_ROOTS: tuple[Path, ...] = (MOVIE_ROOT, SERIES_ROOT)

# --- Whisper (Phase 3) ---
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
WHISPER_MODEL_DIR: str = os.getenv("WHISPER_MODEL_DIR", "/app/models")

# --- Translation ---
SOURCE_LANGUAGE: str = os.getenv("SOURCE_LANGUAGE", "en")
TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "pt-BR")
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://host.containers.internal:11434").rstrip("/")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "translategemma:12b")
OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "5m")
TRANSLATION_BATCH_CUES: int = max(1, int(os.getenv("TRANSLATION_BATCH_CUES", "10")))
TRANSLATION_RETRIES: int = max(1, int(os.getenv("TRANSLATION_RETRIES", "2")))
TRANSLATION_RETRY_DELAY_SECONDS: float = max(
    0.0, float(os.getenv("TRANSLATION_RETRY_DELAY_SECONDS", "1"))
)
TRANSLATION_TIMEOUT_SECONDS: float = max(
    1.0, float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "180"))
)
TRANSLATION_MAX_UNCHANGED_RATIO: float = min(
    1.0, max(0.0, float(os.getenv("TRANSLATION_MAX_UNCHANGED_RATIO", "0.65")))
)

# --- Bazarr integration ---
BAZARR_URL: str = os.getenv("BAZARR_URL", "http://bazarr:6767/api").rstrip("/")
BAZARR_API_KEY: str = os.getenv("BAZARR_API_KEY", "")
BAZARR_DATABASE_PATH: Path = Path(os.getenv("BAZARR_DATABASE", "/bazarr_db/bazarr.db"))

# --- Scheduler ---
SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() in {
    "true", "1", "yes"
}
BATCH_MISSING_INTERVAL_MINUTES: int = max(
    1, int(os.getenv("SCHEDULE_BATCH_MISSING_INTERVAL_MINUTES", "30"))
)
GUARDIAN_INTERVAL_HOURS: int = max(
    1, int(os.getenv("SCHEDULE_GUARDIAN_INTERVAL_HOURS", "6"))
)

# --- Filesystem ---
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "/app/data"))
DATABASE_PATH: Path = DATA_DIR / "subtitle-engine.db"

# --- Probe ---
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    os.getenv("VIDEO_EXTENSIONS", "mkv,mp4,m4v,avi,mov,ts,m2ts").split(",")
)
SUBTITLE_EXTENSIONS: frozenset[str] = frozenset(
    os.getenv("SUBTITLE_EXTENSIONS", "srt,ass,ssa,sub,vtt").split(",")
)
TEXT_SUBTITLE_CODECS: frozenset[str] = frozenset({
    "subrip", "srt", "ass", "ssa", "mov_text", "webvtt",
})
