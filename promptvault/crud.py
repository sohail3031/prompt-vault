from __future__ import annotations

import sqlite3
import re

from typing import Optional
from promptvault.db import Database
from promptvault.model.prompts_entry import PromptsEntry


class DuplicateCommandError(Exception):
    """exception to raise when the duplicate command entered"""

    pass


class InvalidCommandError(Exception):
    """exception to raise when the command is in invalid format"""

    pass


class TagAlreadyAppliedError(Exception):
    """exception to raise when trying to add a tag to a prompt that already has a tag"""

    pass


class TagNotAppliedError(Exception):
    """exception to raise when trying to remove a tag which is not present with the prompt"""

    pass


class PromptNotFoundError(Exception):
    """exception to raise when no prompt was found"""

    pass


class DataOperations:
    def __init__(self) -> None:
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
        """Open a fresh database connection and cursor for this instance.

        Assigns a new `sqlite3.Connection` and `sqlite3.Cursor` to
        `self._connection` and `self._cursor` respectively. Must be called
        at the start of any method that needs database access, since a new
        connection is created per call rather than reused across methods.

        Raises:
            AssertionError: If the connection or cursor unexpectedly comes
                back as None (should not occur under normal operation).
        """
        self._connection = Database().get_connection()

        assert self._connection is not None

        self._cursor = self._connection.cursor()

        assert self._cursor is not None

    def add_prompt(
        self, command: str, title: str, body: str, tags: list[str] | None = None
    ) -> None:
        """Insert a new prompt into the database, optionally tagging it.

        If tags are provided, each tag is looked up or created and linked to
        the new prompt within the same transaction as the insert, so the
        prompt and its tags are committed atomically.

        Args:
            command: Unique, validated identifier used to retrieve this
                prompt later (e.g. 'summarize').
            title: Short, human-readable title for the prompt.
            body: The full prompt text to store.
            tags: Optional list of tag names to associate with the prompt.
                Tags are created automatically if they don't already exist.

        Raises:
            InvalidCommandError: If `command` fails validation (empty,
                malformed, reserved word, etc.).
            DuplicateCommandError: If a prompt with this `command` already
                exists.
            TagAlreadyAppliedError: If a tag in `tags` is somehow already
                linked to this prompt (should not normally occur for a
                brand-new prompt).
            RuntimeError: If the database fails to return an id for the
                newly inserted prompt.
        """
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
                raise RuntimeError("Fail to insert prompt in database")

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
        """Retrieve a single prompt by its command name.

        Args:
            command: The unique command name identifying the prompt.

        Returns:
            The matching `PromptsEntry`, or `None` if no prompt with this
            command exists.

        Raises:
            InvalidCommandError: If `command` fails validation.
        """
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT * FROM prompts WHERE command = ?", (command,))

            row: sqlite3.Row | None = self._cursor.fetchone()
        finally:
            self._connection.close()

        if row is None:
            return None

        return PromptsEntry.from_row(row=row)

    def list_prompts(self) -> list[PromptsEntry]:
        """Retrieve every prompt currently stored in the database.

        Returns:
            A list of all `PromptsEntry` records, in no particular order.
            Returns an empty list if no prompts exist.
        """
        self._create_database_connection()

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

    def update_prompt(self, command: str, title: str | None, body: str | None) -> bool:
        """Update an existing prompt's title and/or body.

        Only the fields explicitly provided (not None) are updated; passing
        None for a field leaves its current value unchanged. If neither
        title nor body is provided, no database write occurs.

        Args:
            command: The unique command name identifying the prompt to
                update. Used only as a lookup key — not itself modified.
            title: New title for the prompt, or None to leave it unchanged.
            body: New body text for the prompt, or None to leave it
                unchanged.

        Returns:
            True if a matching prompt was found and updated, False if no
            prompt with this command exists, or if neither title nor body
            was provided.

        Raises:
            InvalidCommandError: If `command` fails validation.
        """
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
        """Delete a prompt from the database.

        Args:
            command: The unique command name identifying the prompt to
                delete.

        Returns:
            True if a matching prompt was found and deleted, False if no
            prompt with this command exists.

        Raises:
            InvalidCommandError: If `command` fails validation.
        """
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("DELETE FROM prompts WHERE command = ?", (command,))
            self._connection.commit()

            row_count = self._cursor.rowcount
        finally:
            self._connection.close()

        return bool(row_count)

    def _validate_command(self, command: str) -> None:
        """Validate a command name against PromptVault's naming rules.

        A valid command must be non-empty, contain no leading/trailing
        whitespace, be between 1 and 50 characters, start with a lowercase
        letter, contain only lowercase letters, digits, and hyphens
        thereafter, and not collide with a reserved CLI subcommand name
        (e.g. 'add', 'list').

        Args:
            command: The command name to validate.

        Raises:
            InvalidCommandError: If any of the above rules are violated.
                The exception message identifies which specific rule
                failed.
        """
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
        """Look up a tag's id by name, creating the tag if it doesn't exist.

        Tag names are normalized (lowercased and stripped) before lookup,
        so matching is case- and whitespace-insensitive.

        Note:
            Reuses the caller's already-open `self._connection`/
            `self._cursor` rather than opening its own — must only be
            called from within a method that has already called
            `_create_database_connection()`.

        Args:
            tag_name: The tag name to look up or create.

        Returns:
            The tag's id, whether pre-existing or newly created.

        Raises:
            RuntimeError: If a newly inserted tag's id cannot be retrieved.
        """
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
        """Apply a tag to an existing prompt, creating the tag if needed.

        Args:
            command: The unique command name identifying the prompt to tag.
            tag_name: The tag name to apply. Normalized (lowercased and
                stripped) and created automatically if it doesn't already
                exist.

        Raises:
            InvalidCommandError: If `command` fails validation.
            PromptNotFoundError: If no prompt with this command exists.
            TagAlreadyAppliedError: If this tag is already applied to the
                prompt.
        """
        self._validate_command(command=command)
        self._create_database_connection()

        if self._cursor is None:
            raise RuntimeError("Database cursor failed to initialize")

        if self._connection is None:
            raise RuntimeError("Failed to initialize database connection")

        try:
            self._cursor.execute("SELECT id FROM prompts WHERE command=?", (command,))

            prompt_id = self._cursor.fetchone()["id"]
            tag_id = self._get_or_create_tag_id(tag_name=tag_name)
            self._cursor.execute(
                "INSERT INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)",
                (prompt_id, tag_id),
            )
            self._connection.commit()
        except TypeError:
            raise PromptNotFoundError(f"Unable to add Prompt Tag: {tag_name}")
        except sqlite3.IntegrityError as e:
            raise TagAlreadyAppliedError(f"Tag: {tag_name} already exists") from e
        finally:
            self._connection.close()

    def remove_tag_from_prompt(self, command: str, tag_name: str) -> bool:
        """Remove a tag from a prompt, if it's currently applied.

        Unlike `add_tag_to_prompt`, this does not create the tag if it
        doesn't exist — there's nothing to remove in that case.

        Args:
            command: The unique command name identifying the prompt.
            tag_name: The tag name to remove from the prompt.

        Returns:
            True if the tag was found on the prompt and removed, False if
            the tag was never applied to this prompt (or doesn't exist at
            all).

        Raises:
            InvalidCommandError: If `command` fails validation.
            PromptNotFoundError: If no prompt with this command exists.
        """
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
        """Find all prompts tagged with a given tag name.

        Args:
            tag_name: The tag name to search for. Matching is
                case- and whitespace-insensitive.

        Returns:
            A list of matching `PromptsEntry` records. Returns an empty
            list if no prompts have this tag (this is not an error).
        """
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
