"""Translate subtitle files (e.g. EN -> pt-BR) via Google Translate API."""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path

from app import config

LOGGER = logging.getLogger("subtitle-engine.translate")

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def _translate_text_chunk(text: str, source_lang: str, target_lang: str, retries: int = 3) -> str:
    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }
    url = f"{TRANSLATE_URL}?{urllib.parse.urlencode(params)}"

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                import json
                raw = json.loads(resp.read().decode("utf-8"))
                translated = "".join(part[0] for part in raw[0] if part and part[0])
                return translated
        except Exception as err:
            last_err = err
            import time
            time.sleep(1.0 * (attempt + 1))

    raise RuntimeError(f"Translation failed after {retries} retries: {last_err}") from last_err


def translate_srt_content(srt_text: str, source_lang: str = "en", target_lang: str = "pt") -> str:
    """Translate text lines of SRT content while leaving cue numbers and timestamps intact."""
    lines = srt_text.splitlines()
    translated_lines: list[str] = []
    text_buffer: list[str] = []

    def flush_buffer():
        if not text_buffer:
            return
        combined = "\n".join(text_buffer)
        try:
            res = _translate_text_chunk(combined, source_lang, target_lang)
            translated_lines.extend(res.splitlines())
        except Exception as err:
            LOGGER.warning("Translation chunk failed (%s), keeping original text", err)
            translated_lines.extend(text_buffer)
        text_buffer.clear()

    timestamp_re = re.compile(r"^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}")

    for line in lines:
        stripped = line.strip()
        if stripped.isdigit() or timestamp_re.match(stripped) or not stripped:
            flush_buffer()
            translated_lines.append(line)
        else:
            text_buffer.append(line)

    flush_buffer()
    return "\n".join(translated_lines)


def translate_srt_file(input_file: Path, output_file: Path, source_lang: str = "en", target_lang: str = "pt") -> Path:
    """Read an SRT file, translate text blocks, and write to output_file."""
    if not input_file.is_file():
        raise FileNotFoundError(f"Input SRT file not found: {input_file}")

    content = input_file.read_text(encoding="utf-8", errors="replace")
    translated = translate_srt_content(content, source_lang, target_lang)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(translated, encoding="utf-8")
    LOGGER.info("Translated SRT from %s to %s -> %s", source_lang, target_lang, output_file)
    return output_file
