from __future__ import annotations

import sqlite3
import re

from typing import Optional
from promptvault.db import Database
from promptvault.model.prompts_entry import PromptsEntry


class DuplicateCommandError(Exception):
    """Raised when attempting to add a prompt with a command that already exists."""

    pass


class InvalidCommandError(Exception):
    """Raised when a command name fails validation (empty, malformed, reserved, etc.)."""

    pass


class TagAlreadyAppliedError(Exception):
    """Raised when attempting to apply a tag that's already applied to the prompt."""

    pass


class TagNotAppliedError(Exception):
    """Raised when attempting to remove a tag that isn't applied to the prompt."""

    pass


class PromptNotFoundError(Exception):
    """Raised when looking up a prompt by command name finds no match."""

    pass


class DataOperations:
    """Data access layer for PromptVault's SQLite database.

    Provides CRUD operations for prompts and tag management, opening
    and closing a fresh database connection for each method call
    rather than holding one open for the lifetime of the instance.

    Args:
        database: Optional `Database` instance to use for all
            connections. Defaults to a real `Database()` pointed at
            the production data file; tests can pass in a `Database`
            pointed at an isolated temp file instead.
    """

    def __init__(self, database: Optional[Database] = None) -> None:
        self._database: Database = database if database is not None else Database()
        self._connection: sqlite3.Connection | None = None
        self._cursor: sqlite3.Cursor | None = None
        self._reserved_words: list[str] = [
            "add",
            "get",
            "list",
            "update",
            "delete",
            "help",
        ]

    def _create_database_connection(self) -> None:
        """Open a fresh database connection and cursor for this instance."""
        self._connection = self._database.get_connection()

        assert self._connection is not None

        self._cursor = self._connection.cursor()

        assert self._cursor is not None

    def add_prompt(
        self, command: str, title: str, body: str, tags: list[str] | None = None
    ) -> None:
        """Insert a new prompt into the database, optionally tagging it."""
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute(
                "INSERT INTO prompts (command, title, body) VALUES (?, ?, ?)",
                (command, title, body),
            )

            prompt_id: int | None = self._cursor.lastrowid

            if prompt_id is None:
                raise RuntimeError("Failed to insert prompt in database")

            if tags:
                for tag_name in tags:
                    tag_id = self._get_or_create_tag_id(tag_name=tag_name)

                    try:
                        self._cursor.execute(
                            "INSERT INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                            (prompt_id, tag_id),
                        )
                    except sqlite3.IntegrityError as e:
                        raise TagAlreadyAppliedError(
                            f"Tag: {tag_name} already exists"
                        ) from e

            self._connection.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateCommandError(f"The command {command} already exists") from e
        finally:
            self._connection.close()

    def get_prompt(self, command: str) -> Optional[PromptsEntry]:
        """Retrieve a single prompt by its command name."""
        self._validate_command(command=command)
        self._create_database_connection()

        row: sqlite3.Row | None = None

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT * FROM prompts WHERE command = ?", (command,))

            row = self._cursor.fetchone()
        finally:
            self._connection.close()

        if row is None:
            return None

        return PromptsEntry.from_row(row=row)

    def list_prompts(self) -> list[PromptsEntry]:
        """Retrieve every prompt currently stored in the database."""
        self._create_database_connection()

        available_prompts: list[PromptsEntry] = []

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT * FROM prompts")

            rows: list[sqlite3.Row] = self._cursor.fetchall()
            available_prompts = [PromptsEntry.from_row(row) for row in rows]
        finally:
            self._connection.close()

        return available_prompts

    def list_prompts_with_tags(self) -> list[dict[str, object]]:
        """List every prompt alongside its associated tags."""
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute(
                "SELECT p.command, p.title, GROUP_CONCAT(t.name, ', ') AS tags "
                "FROM prompts p "
                "LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id "
                "LEFT JOIN tags t ON pt.tag_id = t.id "
                "GROUP BY p.id;"
            )

            rows: list[sqlite3.Row] = self._cursor.fetchall()
        finally:
            self._connection.close()

        return [dict(row) for row in rows]

    def update_prompt(self, command: str, title: str | None, body: str | None) -> bool:
        """Update an existing prompt's title and/or body."""
        self._validate_command(command=command)
        self._create_database_connection()

        prompt_update: dict[str, object] = {}

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if title is not None:
            prompt_update["title"] = title

        if body is not None:
            prompt_update["body"] = body

        if not prompt_update:
            self._connection.close()

            return False

        set_clause: str = ", ".join(f"{col} = ?" for col in prompt_update)
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        values: list[object] = list(prompt_update.values()) + [command]
        row_count: int = 0

        try:
            self._cursor.execute(
                f"UPDATE prompts SET {set_clause} WHERE command = ?", values
            )
            self._connection.commit()

            row_count = self._cursor.rowcount
        finally:
            self._connection.close()

        return bool(row_count)

    def delete_prompt(self, command: str) -> bool:
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")
        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        row_count: int = 0

        try:
            self._cursor.execute("SELECT id FROM prompts WHERE command = ?", (command,))
            prompt_row = self._cursor.fetchone()

            if prompt_row is not None:
                prompt_id = prompt_row["id"]
                self._cursor.execute(
                    "DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt_id,)
                )
                self._cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
                self._connection.commit()
                row_count = self._cursor.rowcount
        finally:
            self._connection.close()

        return bool(row_count)

    def get_all_commands(self) -> list[str]:
        """Return every prompt's command name, for fuzzy-match suggestions."""
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT command FROM prompts")
            rows: list[sqlite3.Row] = self._cursor.fetchall()
        finally:
            self._connection.close()

        return [row["command"] for row in rows]

    def _validate_command(self, command: str) -> None:
        """Validate a command name against PromptVault's naming rules."""
        if not command or command.isspace():
            raise InvalidCommandError(
                f'The command "{command}" is empty or contains only spaces'
            )

        if command.startswith(" ") or command.endswith(" "):
            raise InvalidCommandError(
                f'The command "{command}" contains spaces at the beginning or at the end of the command'
            )

        if len(command) not in range(1, 51):
            raise InvalidCommandError(
                f'The command "{command}"\'s length is invalid. The command length should be in between 1 and 50 characters'
            )

        if not re.match(r"^[a-z][a-z0-9-]*$", command):
            raise InvalidCommandError(
                f'The command "{command}" contains invalid characters. It should start with a letter and can contains numbers and hyphens.'
            )

        if command in self._reserved_words:
            raise InvalidCommandError(
                f'The command "{command}" contains a reserved word. Try to select some other command.'
            )

    def _get_or_create_tag_id(self, tag_name: str) -> Optional[int]:
        """Look up a tag's id by name, creating the tag if it doesn't exist."""
        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        tag_name = tag_name.lower().strip()

        self._cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))

        row: sqlite3.Row | None = self._cursor.fetchone()

        if row is not None:
            return row["id"]
        else:
            self._cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))

            last_row_id: int | None = self._cursor.lastrowid

            if last_row_id is None:
                raise RuntimeError("Failed to retrieve the inserted row ID")

            return last_row_id

    def add_tag_to_prompt(self, command: str, tag_name: str) -> None:
        """Apply a tag to an existing prompt, creating the tag if needed."""
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT id FROM prompts WHERE command = ?", (command,))
            prompt_row = self._cursor.fetchone()

            if prompt_row is None:
                raise PromptNotFoundError(f"No prompt found with command: {command}")

            prompt_id = prompt_row["id"]
            tag_id = self._get_or_create_tag_id(tag_name=tag_name)

            try:
                self._cursor.execute(
                    "INSERT INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                    (prompt_id, tag_id),
                )
            except sqlite3.IntegrityError as e:
                raise TagAlreadyAppliedError(f"Tag: {tag_name} already exists") from e

            self._connection.commit()
        finally:
            self._connection.close()

    def remove_tag_from_prompt(self, command: str, tag_name: str) -> bool:
        """Remove a tag from a prompt, if it's currently applied."""
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        row_count: int = 0

        try:
            self._cursor.execute("SELECT id FROM prompts WHERE command = ?", (command,))
            prompt_row = self._cursor.fetchone()

            if prompt_row is None:
                raise PromptNotFoundError(f"No prompt found with command: {command}")

            prompt_id = prompt_row["id"]

            tag_name = tag_name.lower().strip()
            self._cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_row = self._cursor.fetchone()

            if tag_row is not None:
                tag_id = tag_row["id"]

                self._cursor.execute(
                    "DELETE FROM prompt_tags WHERE prompt_id = ? AND tag_id = ?",
                    (prompt_id, tag_id),
                )
                self._connection.commit()

                row_count = self._cursor.rowcount
        finally:
            self._connection.close()

        return bool(row_count)

    def search_by_tag(self, tag_name: str) -> list[PromptsEntry]:
        """Find all prompts tagged with a given tag name."""
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        tag_name = tag_name.lower().strip()

        try:
            self._cursor.execute(
                "SELECT p.id, p.command, p.title, p.body, p.created_at, p.updated_at "
                "FROM prompts p "
                "INNER JOIN prompt_tags pt ON p.id = pt.prompt_id "
                "INNER JOIN tags t ON pt.tag_id = t.id "
                "WHERE t.name = ?;",
                (tag_name,),
            )

            rows: list[sqlite3.Row] = self._cursor.fetchall()
        finally:
            self._connection.close()

        return [PromptsEntry.from_row(row) for row in rows]
