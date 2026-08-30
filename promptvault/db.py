from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

import sys

if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle
    BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    BASE_DIR = Path(__file__).parent.parent

SCHEMA_SQL = (BASE_DIR / "schema.sql").read_text()


class Database:
    """Manages the SQLite connection and file location for PromptVault.

    Args:
        db_path: Optional override for where the database file lives.
            Defaults to an OS-appropriate user-data directory (e.g.
            `%APPDATA%\\PromptVault\\` on Windows), resolved via
            `platformdirs` so the app works correctly whether run from
            source or as a packaged executable. Passing an explicit
            path (e.g. a pytest `tmp_path`) lets tests run against an
            isolated, throwaway database instead of the real one.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.DATA_FOLDER = Path(user_data_dir("PromptVault", appauthor=False))
        self.DB_PATH: Path = (
            db_path if db_path is not None else self.DATA_FOLDER / "promptvault.db"
        )

    def _ensure_data_folder_exists(self) -> None:
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        self._ensure_data_folder_exists()

        connection: sqlite3.Connection = sqlite3.connect(
            self.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='prompts'"
        )
        if cursor.fetchone() is None:
            connection.executescript(SCHEMA_SQL)
            connection.commit()

        return connection

    def initialize_schema(self, schema_sql: str) -> None:
        """Execute a schema script against this database.

        Used by the test suite to stand up a fresh set of tables in
        an isolated temp database with a specific schema. Kept for
        backward compatibility with existing tests; production code
        now auto-applies the built-in schema via get_connection().
        """
        connection = self.get_connection()
        try:
            connection.executescript(schema_sql)
            connection.commit()
        finally:
            connection.close()
