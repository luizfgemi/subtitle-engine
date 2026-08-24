"""Tests for the fail-open embedded subtitle cache."""

import sqlite3
from unittest.mock import patch

from app.satisfaction import is_embedded_satisfied, remember_embedded_satisfaction


def test_cache_read_failure_does_not_block_pipeline(tmp_path):
    video = tmp_path / "movie.mkv"
    video.touch()
    with patch(
        "app.satisfaction._connect",
        side_effect=sqlite3.OperationalError("database unavailable"),
    ):
        assert is_embedded_satisfied(video, "pt-BR") is False


def test_cache_write_failure_is_best_effort(tmp_path):
    video = tmp_path / "movie.mkv"
    video.touch()
    with patch(
        "app.satisfaction._connect",
        side_effect=sqlite3.OperationalError("database unavailable"),
    ):
        remember_embedded_satisfaction(video, "pt-BR")
