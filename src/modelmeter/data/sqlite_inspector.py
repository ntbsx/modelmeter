"""Read-only SQLite schema and health inspection."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteInspector:
    """Inspect agent SQLite metadata in read-only mode."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self._db_path}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def sqlite_version(self) -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT sqlite_version() AS version").fetchone()
            if row is None:
                return "unknown"
            return str(row["version"])

    def get_tables(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {str(row["name"]) for row in rows}

    def get_table_columns(self, table_name: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        return {str(row["name"]) for row in rows}

    def count_rows(self, table_name: str) -> int:
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS value FROM {table_name}").fetchone()
        if row is None:
            return 0
        return int(row["value"])
