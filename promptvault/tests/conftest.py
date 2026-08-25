from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from promptvault.crud import DataOperations
from promptvault.db import Database

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS prompt_tags (
    prompt_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (prompt_id, tag_id),
    FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);
"""


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """A Database instance pointed at a fresh, temporary SQLite file.

    Each test gets its own file (via pytest's tmp_path), so tests
    never touch the real data/promptvault.db and never interfere
    with one another.
    """
    db_path = tmp_path / "test_promptvault.db"
    database = Database(db_path=db_path)
    database.initialize_schema(SCHEMA_SQL)

    return database


@pytest.fixture
def data_ops(test_db: Database) -> DataOperations:
    """A DataOperations instance wired to the isolated test database."""
    return DataOperations(database=test_db)


@pytest.fixture
def runner() -> CliRunner:
    """A Click CliRunner for invoking CLI commands in tests."""
    return CliRunner()


@pytest.fixture(autouse=True)
def patch_cli_data_operations(monkeypatch, test_db: Database):
    """Make every `DataOperations()` call inside cli.py use the test DB.

    cli.py always instantiates `DataOperations()` with no arguments,
    which normally binds to the real, production database. This
    fixture is autouse (applies to every test in this package) and
    redirects that call to a DataOperations bound to the isolated
    per-test database instead, so CLI tests never touch real data.
    """

    def factory(*args, **kwargs):
        return DataOperations(database=test_db)

    monkeypatch.setattr("promptvault.cli.DataOperations", factory)
