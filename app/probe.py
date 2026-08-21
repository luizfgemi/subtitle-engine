"""Media probing module using ffprobe to detect audio and subtitle tracks."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app import config

LOGGER = logging.getLogger("subtitle-engine.probe")


@dataclass(frozen=True)
class TrackInfo:
    index: int
    codec_name: str
    codec_type: str  # "audio" or "subtitle"
    language: str
    title: str = ""
    is_default: bool = False
    is_forced: bool = False
    is_commentary: bool = False


@dataclass(frozen=True)
class MediaProbeResult:
    path: Path
    duration_seconds: float
    audio_tracks: list[TrackInfo] = field(default_factory=list)
    subtitle_tracks: list[TrackInfo] = field(default_factory=list)

    @property
    def has_subtitles(self) -> bool:
        return len(self.subtitle_tracks) > 0

    def find_subtitles_by_language(self, lang_code: str) -> list[TrackInfo]:
        aliases = {
            "pt-br": {"por", "pob", "pt", "pt-br", "pt_br"},
            "pt": {"por", "pob", "pt", "pt-br", "pt_br"},
            "por": {"por", "pob", "pt", "pt-br", "pt_br"},
            "pob": {"por", "pob", "pt", "pt-br", "pt_br"},
            "en": {"eng", "en"},
            "eng": {"eng", "en"},
        }
        target = lang_code.casefold()
        target_set = aliases.get(target, {target})

        matches = []
        for track in self.subtitle_tracks:
            track_lang = track.language.casefold()
            if track_lang in target_set:
                matches.append(track)
        return matches

    def best_audio_track(self) -> TrackInfo | None:
        if not self.audio_tracks:
            return None
        # Prefer non-commentary, default/first tracks
        candidates = [t for t in self.audio_tracks if not t.is_commentary]
        if not candidates:
            candidates = self.audio_tracks
        defaults = [t for t in candidates if t.is_default]
        return defaults[0] if defaults else candidates[0]


def probe_media(file_path: Path) -> MediaProbeResult:
    if not file_path.is_file():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    cmd = [
        "ffprobe",
        "-loglevel", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        data: dict[str, Any] = json.loads(res.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError) as err:
        LOGGER.error("Failed to probe media file %s: %s", file_path, err)
        raise RuntimeError(f"ffprobe failed for {file_path}: {err}") from err

    format_info = data.get("format", {})
    duration = float(format_info.get("duration", 0.0))

    audio_tracks: list[TrackInfo] = []
    sub_tracks: list[TrackInfo] = []

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type not in ("audio", "subtitle"):
            continue

        index = int(stream.get("index", 0))
        codec_name = str(stream.get("codec_name", ""))
        tags = stream.get("tags", {})
        disposition = stream.get("disposition", {})

        lang = str(tags.get("language", "und")).lower()
        title = str(tags.get("title", ""))
        is_default = bool(disposition.get("default", 0))
        is_forced = bool(disposition.get("forced", 0))
        is_commentary = bool(disposition.get("comment", 0)) or "commentary" in title.lower()

        track = TrackInfo(
            index=index,
            codec_name=codec_name,
            codec_type=codec_type,
            language=lang,
            title=title,
            is_default=is_default,
            is_forced=is_forced,
            is_commentary=is_commentary,
        )

        if codec_type == "audio":
            audio_tracks.append(track)
        elif codec_type == "subtitle":
            sub_tracks.append(track)

    return MediaProbeResult(
        path=file_path,
        duration_seconds=duration,
        audio_tracks=audio_tracks,
        subtitle_tracks=sub_tracks,
    )
