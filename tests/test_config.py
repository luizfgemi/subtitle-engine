"""Tests for app.config and environment loading."""

from app import config


def test_default_config():
    assert config.API_PORT == 8090
    assert config.WHISPER_MODEL == "large-v3-turbo"
    assert config.TARGET_LANGUAGE == "pt-BR"
    assert "mkv" in config.VIDEO_EXTENSIONS
    assert "srt" in config.SUBTITLE_EXTENSIONS
