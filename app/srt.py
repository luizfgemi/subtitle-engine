"""Parse, render, and preserve formatting in SRT subtitles."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.errors import TranslationError

TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}(?:\s+.*)?$"
)
STYLE_RE = re.compile(r"(<[^>]+>|\{\\[^}]+\})")


@dataclass(frozen=True)
class SrtCue:
    identifier: str
    timestamp: str
    text: str


def parse_srt(content: str) -> list[SrtCue]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise TranslationError("Input subtitle is empty")

    cues: list[SrtCue] = []
    for block_number, block in enumerate(re.split(r"\n{2,}", normalized), start=1):
        lines = block.splitlines()
        if len(lines) < 2:
            raise TranslationError(
                f"Invalid SRT block #{block_number}: missing timestamp or text"
            )

        if TIMESTAMP_RE.match(lines[0].strip()):
            identifier, timestamp_index = str(block_number), 0
        elif len(lines) >= 3 and TIMESTAMP_RE.match(lines[1].strip()):
            identifier, timestamp_index = lines[0].strip(), 1
        else:
            raise TranslationError(
                f"Invalid SRT block #{block_number}: malformed timestamp"
            )

        text = "\n".join(lines[timestamp_index + 1 :]).strip()
        if not text:
            raise TranslationError(f"Invalid SRT block #{block_number}: empty cue")
        cues.append(SrtCue(identifier, lines[timestamp_index], text))
    return cues


def render_srt(cues: list[SrtCue]) -> str:
    return "\n\n".join(
        f"{cue.identifier}\n{cue.timestamp}\n{cue.text}" for cue in cues
    ) + "\n"


def strip_styles(text: str) -> tuple[str, list[tuple[int, str]]]:
    plain_parts: list[str] = []
    styles: list[tuple[int, str]] = []
    source_position = 0
    previous_end = 0
    for match in STYLE_RE.finditer(text):
        visible = text[previous_end : match.start()]
        plain_parts.append(visible)
        source_position += len(visible)
        styles.append((source_position, match.group(0)))
        previous_end = match.end()
    plain_parts.append(text[previous_end:])
    return "".join(plain_parts), styles


def restore_styles(
    translated: str, styles: list[tuple[int, str]], source_text: str
) -> str:
    if not styles:
        return translated

    source_lines = source_text.split("\n")
    translated_lines = translated.split("\n")
    insertions: list[tuple[int, int, str]] = []
    for order, (source_position, style) in enumerate(styles):
        source_prefix = source_text[:source_position]
        line_index = source_prefix.count("\n")
        source_column = len(source_prefix.rsplit("\n", 1)[-1])
        if line_index < len(source_lines) and line_index < len(translated_lines):
            source_length = len(source_lines[line_index])
            translated_length = len(translated_lines[line_index])
            line_start = sum(len(line) + 1 for line in translated_lines[:line_index])
            position = line_start
            if source_length:
                position += round(source_column / source_length * translated_length)
        elif source_position <= 0 or not source_text:
            position = 0
        elif source_position >= len(source_text):
            position = len(translated)
        else:
            position = round(source_position / len(source_text) * len(translated))
        insertions.append((position, order, style))

    result = translated
    for position, _order, style in reversed(insertions):
        result = f"{result[:position]}{style}{result[position:]}"
    return result


def fit_line_breaks(translated: str, source: str) -> str:
    source_lines = source.splitlines()
    if len(source_lines) <= 1:
        return translated.replace("\n", " ").strip()
    words = translated.split()
    if len(words) < len(source_lines):
        return translated

    weights = [max(1, len(line.split())) for line in source_lines]
    total_weight = sum(weights)
    result: list[str] = []
    start = 0
    cumulative_weight = 0
    for line_index, weight in enumerate(weights[:-1]):
        cumulative_weight += weight
        remaining_lines = len(weights) - line_index - 1
        ideal_end = round(cumulative_weight / total_weight * len(words))
        end = max(start + 1, min(ideal_end, len(words) - remaining_lines))
        result.append(" ".join(words[start:end]))
        start = end
    result.append(" ".join(words[start:]))
    return "\n".join(result)
