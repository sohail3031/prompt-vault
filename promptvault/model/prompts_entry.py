from __future__ import annotations

from dataclasses import dataclass, asdict, fields
from typing import Optional, Any
from datetime import datetime

import sqlite3


@dataclass
class PromptsEntry:
    command: str
    title: str
    body: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> PromptsEntry:
        """constructs a PromptEntry from a database row"""
        init_fields: set[str] = {f.name for f in fields(cls) if f.init}
        row_keys: list[str] = row.keys()
        data: dict[str, Any] = {key: row[key] for key in row_keys if key in init_fields}

        return cls(**data)

    def to_db_dict(self, allowed_columns: list[str]) -> dict[str, object]:
        """converts dataclass to a dict"""
        full_dict = asdict(self)
        valid_fields: set[str] = {f.name for f in fields(self)}
        unknown = set(allowed_columns) - valid_fields

        if unknown:
            raise ValueError(f"Unknown columns: {unknown}")

        return {
            key: value for key, value in full_dict.items() if key in allowed_columns
        }
