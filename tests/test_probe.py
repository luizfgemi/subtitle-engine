"""Tests for app.probe module."""

import json
from unittest.mock import patch
import pytest

from app.probe import TrackInfo, MediaProbeResult, probe_media


def test_track_info():
    t = TrackInfo(index=0, codec_name="aac", codec_type="audio", language="eng", is_default=True)
    assert t.index == 0
    assert t.codec_type == "audio"
    assert t.language == "eng"
    assert t.is_default is True


def test_media_probe_result_helpers():
    aud = TrackInfo(index=1, codec_name="ac3", codec_type="audio", language="eng")
    sub_pt = TrackInfo(index=2, codec_name="subrip", codec_type="subtitle", language="por")
    sub_en = TrackInfo(index=3, codec_name="subrip", codec_type="subtitle", language="eng")

    res = MediaProbeResult(
        path="/tmp/video.mkv",
        duration_seconds=120.0,
        audio_tracks=[aud],
        subtitle_tracks=[sub_pt, sub_en],
    )

    assert res.has_subtitles is True
    assert len(res.find_subtitles_by_language("por")) == 1
    assert len(res.find_subtitles_by_language("pt-BR")) == 1
    assert res.best_audio_track() == aud


@patch("subprocess.run")
def test_probe_media_success(mock_run, tmp_path):
    video = tmp_path / "sample.mkv"
    video.touch()

    ffprobe_output = {
        "format": {"duration": "60.5"},
        "streams": [
            {
                "index": 0,
                "codec_name": "h264",
                "codec_type": "video",
            },
            {
                "index": 1,
                "codec_name": "eac3",
                "codec_type": "audio",
                "tags": {"language": "eng"},
                "disposition": {"default": 1},
            },
            {
                "index": 2,
                "codec_name": "subrip",
                "codec_type": "subtitle",
                "tags": {"language": "pob", "title": "Portuguese"},
                "disposition": {"default": 0},
            },
        ],
    }

    mock_run.return_value.stdout = json.dumps(ffprobe_output)
    mock_run.return_value.returncode = 0

    result = probe_media(video)
    assert result.duration_seconds == 60.5
    assert len(result.audio_tracks) == 1
    assert len(result.subtitle_tracks) == 1
    assert result.subtitle_tracks[0].language == "pob"
