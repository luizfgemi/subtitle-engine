"""Translate SRT subtitles with a local model served by Ollama."""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app import config
from app.errors import ProcessingCancelled, TranslationError
from app.prompt import render_prompt
from app.provenance import add_watermark, publish
from app.srt import SrtCue, fit_line_breaks, parse_srt, render_srt, restore_styles, strip_styles

LOGGER = logging.getLogger("subtitle-engine.translate")

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")
MARKER_RE = re.compile(r"^\[(\d{4})\]\s*(.+)$")


def _post_json(url: str, payload: dict[str, object], timeout: float) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise TranslationError("Ollama returned non-object JSON")
    return decoded


def _ollama_translate_batch(
    texts: list[str],
    source_lang: str,
    target_lang: str,
) -> list[str]:
    protected_texts: list[str] = []
    style_maps: list[tuple[list[tuple[int, str]], str]] = []
    for text in texts:
        plain, styles = strip_styles(text)
        protected_texts.append(plain)
        style_maps.append((styles, plain))

    marked_text = "\n".join(
        f"[{index:04d}] {text.replace(chr(10), ' ')}"
        for index, text in enumerate(protected_texts, start=1)
    )
    source_name = "English" if source_lang.lower().startswith("en") else source_lang
    target_name = (
        "Brazilian Portuguese"
        if target_lang.lower() in {"pt", "pt-br", "pb"}
        else target_lang
    )
    prompt = render_prompt(
        source_name=source_name,
        source_code=source_lang,
        target_name=target_name,
        target_code=target_lang,
        text=marked_text,
    )
    endpoint = f"{config.OLLAMA_URL.rstrip('/')}/api/chat"
    response = _post_json(
        endpoint,
        {
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=config.TRANSLATION_TIMEOUT_SECONDS,
    )
    message = response.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise TranslationError("Ollama response is missing message.content")
    parsed: dict[int, str] = {}
    for line in message["content"].splitlines():
        if not line.strip():
            continue
        match = MARKER_RE.match(line.strip())
        if not match:
            raise TranslationError("Ollama returned text without a valid cue marker")
        cue_id = int(match.group(1))
        if cue_id in parsed:
            raise TranslationError(f"Ollama returned duplicate cue marker {cue_id:04d}")
        parsed[cue_id] = match.group(2).strip()

    expected_ids = set(range(1, len(texts) + 1))
    if set(parsed) != expected_ids:
        raise TranslationError("Ollama returned an incomplete translation batch")

    translated: list[str] = []
    for expected_id, style_data in enumerate(style_maps, start=1):
        value = parsed[expected_id]
        if not value:
            raise TranslationError(f"Ollama returned empty text for cue {expected_id}")
        styles, source_text = style_data
        reflowed = fit_line_breaks(value, source_text)
        translated.append(restore_styles(reflowed, styles, source_text))
    return translated


def _translate_batch_with_fallback(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    stop_requested: Callable[[], bool] | None = None,
) -> list[str]:
    last_error: Exception | None = None
    for attempt in range(1, config.TRANSLATION_RETRIES + 1):
        if stop_requested and stop_requested():
            raise ProcessingCancelled
        try:
            return _ollama_translate_batch(texts, source_lang, target_lang)
        except Exception as exc:
            last_error = exc
            LOGGER.warning(
                "Translation batch attempt %s/%s failed (cues=%s): %s",
                attempt,
                config.TRANSLATION_RETRIES,
                len(texts),
                exc,
            )
            if attempt < config.TRANSLATION_RETRIES:
                time.sleep(config.TRANSLATION_RETRY_DELAY_SECONDS * attempt)

    if len(texts) > 1:
        midpoint = len(texts) // 2
        LOGGER.info("Retrying failed translation batch as %s + %s cues", midpoint, len(texts) - midpoint)
        first = _translate_batch_with_fallback(
            texts[:midpoint], source_lang, target_lang, stop_requested
        )
        second = _translate_batch_with_fallback(
            texts[midpoint:], source_lang, target_lang, stop_requested
        )
        return first + second

    raise TranslationError(f"Translation failed for a single cue: {last_error}") from last_error


def _validate_translation(source: list[SrtCue], translated: list[SrtCue]) -> None:
    if len(source) != len(translated):
        raise TranslationError("Translated subtitle cue count does not match source")
    for source_cue, translated_cue in zip(source, translated):
        if source_cue.identifier != translated_cue.identifier or source_cue.timestamp != translated_cue.timestamp:
            raise TranslationError("Translated subtitle changed cue IDs or timestamps")

    candidates = [
        (source_cue.text, translated_cue.text)
        for source_cue, translated_cue in zip(source, translated)
        if len(WORD_RE.findall(source_cue.text)) >= 2
    ]
    if candidates:
        unchanged = sum(1 for original, result in candidates if original.casefold() == result.casefold())
        if unchanged / len(candidates) > config.TRANSLATION_MAX_UNCHANGED_RATIO:
            raise TranslationError(
                f"Translation validation failed: {unchanged}/{len(candidates)} meaningful cues are unchanged"
            )


def translate_srt_content(
    srt_text: str,
    source_lang: str = "en",
    target_lang: str = "pt-BR",
    stop_requested: Callable[[], bool] | None = None,
) -> str:
    """Translate SRT text while preserving identifiers, timestamps, styles, and ordering."""
    source_cues = parse_srt(srt_text)
    translated_cues: list[SrtCue] = []
    for start in range(0, len(source_cues), config.TRANSLATION_BATCH_CUES):
        if stop_requested and stop_requested():
            raise ProcessingCancelled
        batch = source_cues[start : start + config.TRANSLATION_BATCH_CUES]
        translated_texts = _translate_batch_with_fallback(
            [cue.text for cue in batch], source_lang, target_lang, stop_requested
        )
        translated_cues.extend(
            SrtCue(identifier=cue.identifier, timestamp=cue.timestamp, text=text)
            for cue, text in zip(batch, translated_texts)
        )

    _validate_translation(source_cues, translated_cues)
    return render_srt(add_watermark(translated_cues))


def translate_srt_file(
    input_file: Path,
    output_file: Path,
    source_lang: str = "en",
    target_lang: str = "pt-BR",
    stop_requested: Callable[[], bool] | None = None,
) -> Path:
    """Translate an SRT and publish it atomically with a visible watermark."""
    if not input_file.is_file():
        raise FileNotFoundError(f"Input SRT file not found: {input_file}")

    content = input_file.read_text(encoding="utf-8", errors="replace")
    translated = translate_srt_content(
        content, source_lang, target_lang, stop_requested
    )

    publish(output_file, translated)
    LOGGER.info(
        "Translated SRT via Ollama/%s from %s to %s -> %s",
        config.OLLAMA_MODEL,
        source_lang,
        target_lang,
        output_file,
    )
    return output_file
