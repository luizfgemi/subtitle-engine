"""Identify generated subtitles and publish them atomically."""

from __future__ import annotations

from pathlib import Path

from app import __version__, config
from app.prompt import PROMPT_ID
from app.srt import SrtCue


def add_watermark(cues: list[SrtCue]) -> list[SrtCue]:
    watermark = SrtCue(
        "1",
        "00:00:01,000 --> 00:00:04,000",
        f"Tradução automática • modelo: {config.OLLAMA_MODEL}\n"
        f"Subtitle Engine v{__version__} • prompt: {PROMPT_ID}",
    )
    renumbered = [
        SrtCue(str(index), cue.timestamp, cue.text)
        for index, cue in enumerate(cues, start=2)
    ]
    return [watermark, *renumbered]


def publish(output_file: Path, content: str) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output_file.with_name(f".{output_file.name}.tmp")
    temporary_output.write_text(content, encoding="utf-8")
    temporary_output.replace(output_file)
