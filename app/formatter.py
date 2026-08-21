"""Subtitle formatting utilities for SRT formatting and cleaning."""

from __future__ import annotations

import re


def format_timestamp(seconds: float) -> str:
    """Convert floating seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def sanitize_srt_text(text: str) -> str:
    """Clean up formatting, remove duplicate empty lines and extra whitespace."""
    lines = text.splitlines()
    cleaned: list[str] = []
    prev_empty = False

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            if not prev_empty:
                cleaned.append("")
                prev_empty = True
        else:
            cleaned.append(stripped)
            prev_empty = False

    return "\n".join(cleaned).strip() + "\n"
