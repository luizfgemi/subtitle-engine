"""Tests for app.guardian module."""

from pathlib import Path
from app.guardian import find_orphan_subtitles, cleanup_orphan_subtitles, audit_subtitle_sync


def test_find_orphan_subtitles_empty(tmp_path):
    media_dir = tmp_path / "movies"
    media_dir.mkdir()
    # Video file with matching subtitle -> not an orphan
    video = media_dir / "movie.mkv"
    video.touch()
    sub = media_dir / "movie.pt-BR.srt"
    sub.touch()

    orphans = find_orphan_subtitles(minimum_age_hours=0.0, media_roots=(media_dir,))
    assert len(orphans) == 0


def test_find_orphan_subtitles_detected(tmp_path):
    media_dir = tmp_path / "movies"
    media_dir.mkdir()
    # Subtitle file without video file -> orphan candidate
    orphan_sub = media_dir / "deleted_movie.pt-BR.srt"
    orphan_sub.touch()

    orphans = find_orphan_subtitles(minimum_age_hours=-1.0, media_roots=(media_dir,))
    assert len(orphans) == 1
    assert orphans[0] == orphan_sub


def test_cleanup_orphan_subtitles_dry_run(tmp_path):
    media_dir = tmp_path / "movies"
    media_dir.mkdir()
    orphan_sub = media_dir / "deleted_movie.pt-BR.srt"
    orphan_sub.touch()

    candidates, deleted = cleanup_orphan_subtitles(apply=False, minimum_age_hours=-1.0)
    # File should still exist on disk after dry-run
    assert orphan_sub.exists()
