"""Extract embedded subtitle tracks from video files using ffmpeg."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app import config

LOGGER = logging.getLogger("subtitle-engine.extract")


def extract_subtitle_track(video_path: Path, stream_index: int, output_path: Path) -> Path:
    """Extract an embedded subtitle track to an external SRT file."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_path),
        "-map", f"0:{stream_index}",
        "-c:s", "srt",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
    except (subprocess.SubprocessError, OSError) as err:
        LOGGER.error("Failed to extract subtitle track %d from %s: %s", stream_index, video_path, err)
        if output_path.exists():
            output_path.unlink()
        raise RuntimeError(f"ffmpeg extraction failed: {err}") from err

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Extracted subtitle file is empty or missing: {output_path}")

    LOGGER.info("Successfully extracted track %d from %s to %s", stream_index, video_path, output_path)
    return output_path
