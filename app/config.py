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

# --- Bazarr integration ---
BAZARR_URL: str = os.getenv("BAZARR_URL", "http://bazarr:6767/api").rstrip("/")
BAZARR_API_KEY: str = os.getenv("BAZARR_API_KEY", "")
BAZARR_DATABASE_PATH: Path = Path(os.getenv("BAZARR_DATABASE", "/bazarr_db/bazarr.db"))

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
