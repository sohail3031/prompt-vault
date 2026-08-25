from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """Manages the SQLite connection and file location for PromptVault.

    Args:
        db_path: Optional override for where the database file lives.
            Defaults to `<project_root>/data/promptvault.db`. Passing
            an explicit path (e.g. a pytest `tmp_path`) lets tests run
            against an isolated, throwaway database instead of the
            real one.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.DATA_FOLDER = Path(__file__).parent.parent / "data"
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

        return connection

    def initialize_schema(self, schema_sql: str) -> None:
        """Execute a schema script against this database.

        Used by the test suite to stand up a fresh set of tables in
        an isolated temp database. Not used by the CLI at runtime —
        the real database's schema is created once via schema.sql.
        """
        connection = self.get_connection()
        try:
            connection.executescript(schema_sql)
            connection.commit()
        finally:
            connection.close()
