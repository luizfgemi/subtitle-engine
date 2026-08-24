"""Speech-to-text audio transcription using faster-whisper."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app import config
from app.formatter import format_timestamp, sanitize_srt_text

LOGGER = logging.getLogger("subtitle-engine.transcribe")

_model_instance: Any = None
_model_lock = threading.Lock()


def get_whisper_model():
    """Lazy initialization of faster-whisper model with thread safety."""
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    with _model_lock:
        if _model_instance is not None:
            return _model_instance

        try:
            from faster_whisper import WhisperModel
        except ImportError as err:
            LOGGER.error("faster-whisper library is not installed: %s", err)
            raise RuntimeError("faster-whisper library unavailable") from err

        LOGGER.info("Loading Whisper model '%s' (device=%s, compute_type=%s, download_root=%s)...",
                    config.WHISPER_MODEL, config.WHISPER_DEVICE, config.WHISPER_COMPUTE_TYPE, config.WHISPER_MODEL_DIR)

        Path(config.WHISPER_MODEL_DIR).mkdir(parents=True, exist_ok=True)

        try:
            _model_instance = WhisperModel(
                model_size_or_path=config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
                download_root=config.WHISPER_MODEL_DIR,
            )
        except Exception as err:
            LOGGER.warning("Failed to initialize Whisper on %s (%s). Falling back to CPU...", config.WHISPER_DEVICE, err)
            _model_instance = WhisperModel(
                model_size_or_path=config.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
                download_root=config.WHISPER_MODEL_DIR,
            )
        return _model_instance


def transcribe_audio_to_srt(video_path: Path, output_srt: Path, language: str = "en") -> Path:
    """Transcribe video audio using faster-whisper and write formatted SRT file."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    model = get_whisper_model()
    LOGGER.info("Starting Whisper transcription for %s (language=%s)...", video_path, language)

    segments, info = model.transcribe(
        str(video_path),
        language=language if language != "auto" else None,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    srt_lines: list[str] = []
    cue_index = 1

    LOGGER.info("Transcribing audio segments with Whisper for %s...", video_path.name)
    for segment in segments:
        start_ts = format_timestamp(segment.start)
        end_ts = format_timestamp(segment.end)
        text = segment.text.strip()

        if not text:
            continue

        srt_lines.append(f"{cue_index}")
        srt_lines.append(f"{start_ts} --> {end_ts}")
        srt_lines.append(text)
        srt_lines.append("")

        if cue_index % 50 == 0:
            LOGGER.info("[%s] Whisper progress: transcribed %d cues (current timestamp: %s)", video_path.name, cue_index, start_ts)

        cue_index += 1

    srt_content = sanitize_srt_text("\n".join(srt_lines))
    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_srt.write_text(srt_content, encoding="utf-8")

    LOGGER.info("Whisper transcription completed (%d cues total) -> %s", cue_index - 1, output_srt.name)
    return output_srt
