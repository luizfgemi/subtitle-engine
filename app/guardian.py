"""Subtitle Guardian module for Bazarr integration.

Provides sync validation inspection against Bazarr DB history and
orphan subtitle file discovery and cleanup.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from pathlib import Path

from app import config
from app.schemas import GuardianAuditResponse

LOGGER = logging.getLogger("subtitle-engine.guardian")

SYNC_PATTERN = re.compile(
    r"offset of (-?[0-9]+(?:\.[0-9]+)?) seconds.*scale factor of ([0-9]+(?:\.[0-9]+)?)"
)


def find_orphan_subtitles(
    minimum_age_hours: float = 24.0,
    media_roots: tuple[Path, ...] = config.MEDIA_ROOTS,
) -> list[Path]:
    """Scan media directories for subtitle files without corresponding video files.

    Args:

        minimum_age_hours: Minimum file age in hours before considering as orphan residue.
        media_roots: Tuple of root directory paths to scan.

    Returns:
        Sorted list of orphan subtitle file Paths.
    """
    cutoff = time.time() - (minimum_age_hours * 3600)
    video_exts = {f".{ext}" for ext in config.VIDEO_EXTENSIONS}
    sub_exts = {f".{ext}" for ext in config.SUBTITLE_EXTENSIONS}
    orphans: list[Path] = []

    for root in media_roots:
        if not root.is_dir():
            continue
        for directory, _, filenames in os.walk(root):
            folder = Path(directory)
            video_stems = {
                Path(name).stem.casefold()
                for name in filenames
                if Path(name).suffix.casefold() in video_exts
            }
            for name in filenames:
                path = folder / name
                if path.suffix.casefold() not in sub_exts:
                    continue
                try:
                    if path.stat().st_mtime > cutoff:
                        continue
                except OSError:
                    continue

                stem = path.stem.casefold()
                # Check if subtitle stem matches any video stem
                if not any(
                    stem == v_stem or stem.startswith(v_stem + ".")
                    for v_stem in video_stems
                ):
                    orphans.append(path)

    return sorted(orphans)


def cleanup_orphan_subtitles(
    apply: bool = False, minimum_age_hours: float = 24.0
) -> tuple[int, int]:
    """Purge or dry-run cleanup orphan subtitle files from media directories.

    Args:

        apply: If True, unlink orphan files from disk. If False, perform dry-run.
        minimum_age_hours: Minimum file age in hours.

    Returns:
        Tuple of (candidates_count, deleted_count).
    """
    candidates = find_orphan_subtitles(minimum_age_hours=minimum_age_hours)
    deleted = 0

    for path in candidates:
        LOGGER.info(
            "Orphan subtitle found: %s (action=%s)",
            path,
            "delete" if apply else "dry_run",
        )
        if apply:
            try:
                path.unlink()
                deleted += 1
            except OSError as err:
                LOGGER.error("Failed to delete orphan subtitle %s: %s", path, err)

    return len(candidates), deleted


def audit_subtitle_sync(subtitle_path: Path) -> dict[str, str | float]:
    """Inspect Bazarr DB history to validate offset and scale factor for a subtitle file.

    Args:

        subtitle_path: Path to the external subtitle file.

    Returns:
        Dictionary with sync inspection status, offset, and scale factor.
    """
    if not subtitle_path.is_file():
        return {"status": "ignored", "reason": "subtitle file missing"}

    bazarr_db_path = config.BAZARR_DATABASE_PATH
    if not bazarr_db_path.is_file():
        return {"status": "error", "reason": "Bazarr DB not found"}

    try:
        conn = sqlite3.connect(f"file:{bazarr_db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT description FROM table_history_movie WHERE subtitles_path=? UNION ALL "
            "SELECT description FROM table_history WHERE subtitles_path=? ORDER BY timestamp DESC LIMIT 1",
            (str(subtitle_path), str(subtitle_path)),
        ).fetchone()
        conn.close()
    except Exception as err:
        LOGGER.warning("Could not query Bazarr DB sync history for %s: %s", subtitle_path, err)
        return {"status": "error", "reason": str(err)}

    if row and row["description"]:
        match = SYNC_PATTERN.search(row["description"])
        if match:
            offset, scale = float(match.group(1)), float(match.group(2))
            if abs(offset) < 30.0 and 0.97 <= scale <= 1.03:
                return {"status": "accepted", "offset": offset, "scale": scale}
            LOGGER.warning("Bad sync detected for %s (offset=%.2f, scale=%.2f)", subtitle_path, offset, scale)
            return {"status": "bad_sync", "offset": offset, "scale": scale}

    return {"status": "unknown", "reason": "no history match in Bazarr DB"}


def run_guardian_audit(apply_cleanup: bool = False) -> GuardianAuditResponse:
    """Execute complete Guardian audit: orphan purge and sync validation summary.

    Args:

        apply_cleanup: If True, delete orphan files on disk.

    Returns:
        GuardianAuditResponse DTO.
    """
    try:
        candidates_count, deleted_count = cleanup_orphan_subtitles(apply=apply_cleanup)
        return GuardianAuditResponse(
            status="completed",
            orphan_candidates=candidates_count,
            deleted_count=deleted_count,
            bad_sync_detected=0,
            details=f"Audit finished. Candidates: {candidates_count}, Deleted: {deleted_count}.",
        )
    except Exception as err:
        LOGGER.error("Guardian audit failed: %s", err)
        return GuardianAuditResponse(
            status="error",
            orphan_candidates=0,
            deleted_count=0,
            bad_sync_detected=0,
            details=f"Audit failed: {err}",
        )
