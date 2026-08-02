import sqlite3
from pathlib import Path


class Database:
    def __init__(self) -> None:
        self.DATA_FOLDER = Path(__file__).parent.parent / "data"
        self.DB_PATH = self.DATA_FOLDER / "promptvault.db"

    def _ensure_data_folder_exists(self) -> None:
        self.DATA_FOLDER.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        self._ensure_data_folder_exists()

        connection: sqlite3.Connection = sqlite3.connect(
            self.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES
        )
        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        return connection
