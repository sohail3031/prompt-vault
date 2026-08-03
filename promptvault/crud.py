import sqlite3
import re
from typing import Optional
from promptvault.db import Database
from promptvault.model.prompts_entry import PromptsEntry


class DuplicateCommandError(Exception):
    """exception raised when the duplicate command entered"""

    pass


class InvalidCommandError(Exception):
    """exception raised when the command is in invalid format"""

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
        """create connection to database"""
        _database: Database = Database()
        self._connection = _database.get_connection()
        self._cursor = self._connection.cursor()

    def add_prompt(self, command: str, title: str, body: str) -> None:
        """add new Prompt in the database"""
        self._validate_command(command=command)
        self._create_database_connection()

        try:
            self._cursor.execute(
                "INSERT INTO prompts (command, title, body) VALUES (?, ?, ?)",
                (command, title, body),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateCommandError(f"The command {command} already exists") from e
        finally:
            self._connection.close()

    def get_prompt(self, command: str) -> Optional[PromptsEntry]:
        """get the Prompt from the database"""
        self._validate_command(command=command)
        self._create_database_connection()
        self._cursor.execute("SELECT * FROM prompts WHERE command = ?", (command,))

        row: sqlite3.Row | None = self._cursor.fetchone()

        self._connection.close()

        if row is None:
            return None

        return PromptsEntry.from_row(row=row)

    def list_prompts(self) -> list[PromptsEntry]:
        """get all the prompts from the database"""
        self._create_database_connection()
        self._cursor.execute("SELECT * FROM prompts")

        rows: list[sqlite3.Row] = self._cursor.fetchall()
        available_prompts: list[PromptsEntry] = [
            PromptsEntry.from_row(row) for row in rows
        ]

        self._connection.close()

        return available_prompts

    def update_prompt(self, command: str, title: str | None, body: str | None) -> bool:
        """update the prompt in the database"""
        self._validate_command(command=command)
        self._create_database_connection()

        prompt_update: dict[str, object] = {}

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

        self._cursor.execute(
            f"UPDATE prompts SET {set_clause} WHERE command = ?", values
        )
        self._connection.commit()

        row_count: int = self._cursor.rowcount

        self._connection.close()

        return bool(row_count)

    def delete_prompt(self, command: str) -> bool:
        """delete prompt from the database"""
        self._validate_command(command=command)
        self._create_database_connection()
        self._cursor.execute("DELETE FROM prompts WHERE command = ?", (command,))
        self._connection.commit()

        row_count: int = self._cursor.rowcount

        self._connection.close()

        return bool(row_count)

    def _validate_command(self, command: str) -> None:
        """check the command for validity"""
        if not command or command.isspace():
            raise InvalidCommandError(
                f'The command "{command}" is empty or contains only spaces'
            )

        if command.startswith(" ") or command.endswith(" "):
            raise InvalidCommandError(
                f'The command "{command}" contains spaces at the beginning or at the end of the command'
            )

        if len(command) not in range(1, 50):
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
