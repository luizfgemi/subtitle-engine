"""Cache videos whose embedded subtitle already satisfies a language."""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

from app import config

LOGGER = logging.getLogger("subtitle-engine.satisfaction")


def _connect() -> sqlite3.Connection:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.DATABASE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS embedded_satisfaction (
            path TEXT NOT NULL,
            language TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            PRIMARY KEY (path, language)
        )
        """
    )
    return connection


def is_embedded_satisfied(video: Path, language: str) -> bool:
    try:
        stat = video.stat()
        with _connect() as connection:
            row = connection.execute(
                "SELECT size, mtime_ns FROM embedded_satisfaction WHERE path = ? AND language = ?",
                (str(video), language.casefold()),
            ).fetchone()
        return row == (stat.st_size, stat.st_mtime_ns)
    except (OSError, sqlite3.Error) as err:
        LOGGER.warning("Embedded satisfaction cache unavailable: %s", err)
        return False


def remember_embedded_satisfaction(video: Path, language: str) -> None:
    try:
        stat = video.stat()
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO embedded_satisfaction (path, language, size, mtime_ns)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path, language) DO UPDATE SET
                    size = excluded.size,
                    mtime_ns = excluded.mtime_ns
                """,
                (str(video), language.casefold(), stat.st_size, stat.st_mtime_ns),
            )
    except (OSError, sqlite3.Error) as err:
        LOGGER.warning("Could not update embedded satisfaction cache: %s", err)
