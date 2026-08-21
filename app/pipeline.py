"""Subtitle processing pipeline: probe -> extract / transcribe -> translate -> save."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app import config
from app.extract import extract_subtitle_track
from app.probe import probe_media
from app.transcribe import transcribe_audio_to_srt
from app.translate import translate_srt_file

LOGGER = logging.getLogger("subtitle-engine.pipeline")


@dataclass
class PipelineResult:
    video_path: Path
    output_srt: Path | None
    status: str  # "extracted", "extracted_and_translated", "whisper_transcribed", "whisper_transcribed_and_translated", "already_exists", "failed"
    source_method: str  # "embedded_pt_sub", "embedded_en_sub", "whisper_asr"
    details: str = ""


def process_video_subtitles(video_path: Path, target_lang: str = "pt-BR") -> PipelineResult:
    """Main pipeline for a single video file."""
    if not video_path.is_file():
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="",
            details=f"Video file not found: {video_path}",
        )

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

    # 3. Check for existing embedded pt-BR subtitles
    pt_subs = probe_res.find_subtitles_by_language("pt-BR")
    if pt_subs:
        track = pt_subs[0]
        try:
            extracted = extract_subtitle_track(video_path, track.index, target_srt)
            return PipelineResult(
                video_path=video_path,
                output_srt=extracted,
                status="extracted",
                source_method="embedded_pt_sub",
                details=f"Extracted embedded Portuguese track #{track.index}",
            )
        except Exception as err:
            LOGGER.warning("Failed to extract embedded PT sub: %s", err)

    # 4. Check for embedded EN subtitles to translate
    en_subs = probe_res.find_subtitles_by_language("en")
    if en_subs:
        track = en_subs[0]
        temp_en_srt = video_path.with_name(f"{video_path.stem}.temp_en.srt")
        try:
            extract_subtitle_track(video_path, track.index, temp_en_srt)
            translate_srt_file(temp_en_srt, target_srt, source_lang="en", target_lang="pt")
            if temp_en_srt.exists():
                temp_en_srt.unlink()
            return PipelineResult(
                video_path=video_path,
                output_srt=target_srt,
                status="extracted_and_translated",
                source_method="embedded_en_sub",
                details=f"Extracted EN track #{track.index} and translated to pt-BR",
            )
        except Exception as err:
            LOGGER.warning("Failed to extract & translate EN sub: %s", err)
            if temp_en_srt.exists():
                temp_en_srt.unlink()

    # 5. Fallback: Whisper ASR Transcription
    temp_whisper_en = video_path.with_name(f"{video_path.stem}.temp_whisper_en.srt")
    try:
        transcribe_audio_to_srt(video_path, temp_whisper_en, language="en")
        translate_srt_file(temp_whisper_en, target_srt, source_lang="en", target_lang="pt")
        if temp_whisper_en.exists():
            temp_whisper_en.unlink()
        return PipelineResult(
            video_path=video_path,
            output_srt=target_srt,
            status="whisper_transcribed_and_translated",
            source_method="whisper_asr",
            details="Transcribed audio via Whisper ASR (EN) and translated to pt-BR",
        )
    except Exception as err:
        LOGGER.error("Whisper transcription failed for %s: %s", video_path, err)
        if temp_whisper_en.exists():
            temp_whisper_en.unlink()
        return PipelineResult(
            video_path=video_path,
            output_srt=None,
            status="failed",
            source_method="whisper_asr",
            details=f"Whisper ASR failed: {err}",
        )
