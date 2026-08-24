"""Tests for subtitle extraction, translation, Whisper ASR and pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.extract import extract_subtitle_track
from app.pipeline import process_video_subtitles
from app.probe import MediaProbeResult, TrackInfo
from app.translate import translate_srt_content


@pytest.fixture(autouse=True)
def isolated_satisfaction_database(tmp_path):
    with patch("app.config.DATABASE_PATH", tmp_path / "state.db"):
        yield


def test_translate_srt_content():
    raw_srt = (
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "Hello world\n\n"
        "2\n"
        "00:00:05,000 --> 00:00:08,000\n"
        "Good morning\n"
    )

    with patch("app.translate._translate_batch_with_fallback") as mock_trans:
        mock_trans.side_effect = lambda texts, _source, _target, _stop: [
            text.replace("Hello world", "Olá mundo").replace("Good morning", "Bom dia")
            for text in texts
        ]
        res = translate_srt_content(raw_srt, "en", "pt")
        assert "Olá mundo" in res
        assert "Bom dia" in res
        assert "00:00:01,000 --> 00:00:04,000" in res


def test_process_video_already_exists(tmp_path):
    video = tmp_path / "movie.mkv"
    video.touch()
    srt = tmp_path / "movie.pt-BR.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nTeste\n")

    res = process_video_subtitles(video)
    assert res.status == "already_exists"
    assert res.output_srt == srt


@patch("app.pipeline.probe_media")
@patch("app.pipeline.extract_subtitle_track")
def test_embedded_portuguese_is_remembered_without_extraction(
    mock_extract, mock_probe, tmp_path
):
    video = tmp_path / "movie.mkv"
    video.touch()
    mock_probe.return_value = MediaProbeResult(
        path=video,
        duration_seconds=100.0,
        subtitle_tracks=[
            TrackInfo(
                index=2,
                codec_name="subrip",
                codec_type="subtitle",
                language="pob",
            )
        ],
    )

    first = process_video_subtitles(video)
    second = process_video_subtitles(video)

    assert first.status == second.status == "already_exists"
    assert first.source_method == second.source_method == "embedded_pt_sub"
    assert first.output_srt is second.output_srt is None
    mock_probe.assert_called_once_with(video)
    mock_extract.assert_not_called()


@patch("app.pipeline.probe_media")
@patch("app.pipeline.extract_subtitle_track")
@patch("app.pipeline.translate_srt_file")
def test_forced_portuguese_does_not_hide_full_english_subtitle(
    mock_translate, mock_extract, mock_probe, tmp_path
):
    video = tmp_path / "movie.mkv"
    video.touch()
    mock_probe.return_value = MediaProbeResult(
        path=video,
        duration_seconds=100.0,
        subtitle_tracks=[
            TrackInfo(2, "subrip", "subtitle", "pob", is_forced=True),
            TrackInfo(3, "subrip", "subtitle", "eng"),
        ],
    )

    result = process_video_subtitles(video)

    assert result.status == "extracted_and_translated"
    mock_extract.assert_called_once()
    mock_translate.assert_called_once()


@patch("app.pipeline.probe_media")
@patch("app.pipeline.extract_subtitle_track")
@patch("app.pipeline.translate_srt_file")
def test_process_video_embedded_en(mock_translate, mock_extract, mock_probe, tmp_path):
    video = tmp_path / "movie.mkv"
    video.touch()

    mock_probe.return_value = MediaProbeResult(
        path=video,
        duration_seconds=100.0,
        subtitle_tracks=[TrackInfo(index=2, codec_name="subrip", codec_type="subtitle", language="eng")],
    )

    res = process_video_subtitles(video)
    assert res.status == "extracted_and_translated"
    assert res.source_method == "embedded_en_sub"
    mock_extract.assert_called_once()
    mock_translate.assert_called_once()


@patch("app.pipeline.probe_media")
@patch("app.pipeline.extract_subtitle_track")
@patch("app.pipeline.translate_srt_file")
def test_process_video_keeps_english_source_when_translation_fails(
    mock_translate, mock_extract, mock_probe, tmp_path
):
    video = tmp_path / "movie.mkv"
    video.touch()
    mock_probe.return_value = MediaProbeResult(
        path=video,
        duration_seconds=100.0,
        subtitle_tracks=[
            TrackInfo(index=2, codec_name="subrip", codec_type="subtitle", language="eng")
        ],
    )

    def create_source(_video, _track, output):
        output.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        return output

    mock_extract.side_effect = create_source
    mock_translate.side_effect = RuntimeError("model unavailable")

    result = process_video_subtitles(video)

    retained = tmp_path / "movie.temp_en.srt"
    assert result.status == "failed"
    assert result.source_method == "embedded_en_sub"
    assert retained.is_file()
    assert not (tmp_path / "movie.pt-BR.srt").exists()


@patch("app.pipeline.probe_media")
@patch("app.pipeline.transcribe_audio_to_srt")
@patch("app.pipeline.translate_srt_file")
def test_process_video_whisper_fallback(mock_translate, mock_transcribe, mock_probe, tmp_path):
    video = tmp_path / "movie.mkv"
    video.touch()

    mock_probe.return_value = MediaProbeResult(
        path=video,
        duration_seconds=100.0,
        audio_tracks=[TrackInfo(index=1, codec_name="aac", codec_type="audio", language="eng")],
        subtitle_tracks=[],
    )

    res = process_video_subtitles(video)
    assert res.status == "whisper_transcribed_and_translated"
    assert res.source_method == "whisper_asr"
    mock_transcribe.assert_called_once()
    mock_translate.assert_called_once()
