"""Subtitle processing pipeline: probe -> extract / transcribe -> translate -> save."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app import config
from app.extract import extract_subtitle_track
from app.errors import ProcessingCancelled
from app.models import PipelineResult
from app.probe import probe_media
from app.satisfaction import is_embedded_satisfied, remember_embedded_satisfaction
from app.transcribe import transcribe_audio_to_srt
from app.translate import translate_srt_file

LOGGER = logging.getLogger("subtitle-engine.pipeline")


def process_video_subtitles(
    video_path: Path,
    target_lang: str = "pt-BR",
    stop_requested: Callable[[], bool] | None = None,
) -> PipelineResult:
    """Main pipeline for a single video file."""
    if not video_path.is_file():
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="",
            details=f"Video file not found: {video_path}",
        )
    if stop_requested and stop_requested():
        return PipelineResult(video_path, None, "cancelled", "", "Processing cancelled")

    # 1. Target output path (e.g. Movie.pt-BR.srt)
    target_srt = video_path.with_name(f"{video_path.stem}.{target_lang}.srt")
    if target_srt.is_file() and target_srt.stat().st_size > 0:
        return PipelineResult(
            video_path=video_path,
            output_srt=target_srt,
            status="already_exists",
            source_method="existing_file",
            details="Target subtitle already exists",
        )

    if is_embedded_satisfied(video_path, target_lang):
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="already_exists",
            source_method="embedded_pt_sub",
            details="Usable embedded target-language subtitle already exists",
        )

    # 2. Probe video
    try:
        probe_res = probe_media(video_path)
    except Exception as err:
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="",
            details=f"Probe failed: {err}",
        )

    if stop_requested and stop_requested():
        return PipelineResult(video_path, None, "cancelled", "", "Processing cancelled")

    # 3. Check for existing embedded pt-BR subtitles
    pt_subs = [
        track
        for track in probe_res.find_subtitles_by_language(target_lang)
        if not track.is_forced and not track.is_commentary
    ]
    if pt_subs:
        remember_embedded_satisfaction(video_path, target_lang)
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="already_exists",
            source_method="embedded_pt_sub",
            details=f"Usable embedded target-language track #{pt_subs[0].index} already exists",
        )

    # 4. Check for embedded EN subtitles to translate
    en_subs = probe_res.find_subtitles_by_language("en")
    if en_subs:
        track = en_subs[0]
        temp_en_srt = video_path.with_name(f"{video_path.stem}.temp_en.srt")
        try:
            extract_subtitle_track(video_path, track.index, temp_en_srt)
        except Exception as err:
            LOGGER.warning("Failed to extract embedded EN sub: %s", err)
            if temp_en_srt.exists():
                temp_en_srt.unlink()
        else:
            try:
                translate_srt_file(
                    temp_en_srt,
                    target_srt,
                    source_lang=config.SOURCE_LANGUAGE,
                    target_lang=target_lang,
                    stop_requested=stop_requested,
                )
            except ProcessingCancelled:
                return PipelineResult(
                    video_path, None, "cancelled", "embedded_en_sub", "Processing cancelled"
                )
            except Exception as err:
                LOGGER.error("Failed to translate embedded EN sub: %s", err)
                return PipelineResult(
                    video_path=video_path,
                    output_srt=None,
                    status="failed",
                    source_method="embedded_en_sub",
                    details=f"Translation failed; source subtitle retained at {temp_en_srt}: {err}",
                )
            temp_en_srt.unlink(missing_ok=True)
            return PipelineResult(
                video_path=video_path,
                output_srt=target_srt,
                status="extracted_and_translated",
                source_method="embedded_en_sub",
                details=f"Extracted EN track #{track.index} and translated to {target_lang}",
            )

    # 5. Fallback: Whisper ASR Transcription
    temp_whisper_en = video_path.with_name(f"{video_path.stem}.temp_whisper_en.srt")
    try:
        if stop_requested and stop_requested():
            return PipelineResult(video_path, None, "cancelled", "", "Processing cancelled")
        transcribe_audio_to_srt(video_path, temp_whisper_en, language="en")
    except Exception as err:
        LOGGER.error("Whisper transcription failed for %s: %s", video_path, err)
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="whisper_asr",
            details=f"Whisper ASR failed: {err}",
        )

    try:
        translate_srt_file(
            temp_whisper_en,
            target_srt,
            source_lang=config.SOURCE_LANGUAGE,
            target_lang=target_lang,
            stop_requested=stop_requested,
        )
    except ProcessingCancelled:
        return PipelineResult(
            video_path, None, "cancelled", "whisper_asr", "Processing cancelled"
        )
    except Exception as err:
        LOGGER.error("Failed to translate Whisper subtitle for %s: %s", video_path, err)
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="whisper_asr",
            details=f"Translation failed; Whisper subtitle retained at {temp_whisper_en}: {err}",
        )
    temp_whisper_en.unlink(missing_ok=True)
    return PipelineResult(
        video_path=video_path,
        output_srt=target_srt,
        status="whisper_transcribed_and_translated",
        source_method="whisper_asr",
        details=f"Transcribed audio via Whisper ASR (EN) and translated to {target_lang}",
    )
