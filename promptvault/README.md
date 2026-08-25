# PromptVault

A personal CLI tool for storing, tagging, and retrieving reusable AI prompts —
built with Python, Click, and SQLite.

```
$ promptvault add --command summarize --title "Summarize" --body "Summarize the following text." --tags "writing,productivity"
The prompt summarize was added successfully!

$ promptvault get --command summarize
summarize
Summarize
Summarize the following text.
```

## Project status

- [x] Phase 1 — Project scaffolding
- [x] Phase 2 — Core CRUD (`add`, `get`, `list`, `update`, `delete`)
- [x] Phase 3 — Tagging & tag-based search (`tag add`, `tag remove`, `search`)
- [x] Phase 4 — CLI polish (`--version`, delete confirmation, fuzzy `get` suggestions,
      shared error handling, formatted `list` output)
- [x] Phase 5 — Tests & documentation
- [ ] Phase 6 — Web-based UI (planned, not started)

## Data model

Three tables, connected many-to-many for tags:

```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE prompt_tags (
    prompt_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (prompt_id, tag_id),
    FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);
```

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the reasoning behind this schema
and the rest of the codebase's design.

## Setup

```powershell
git clone <repo-url>
cd promptvault
pip install -e ".[dev]"
Get-Content schema.sql | sqlite3 data\promptvault.db
pre-commit install
```

## Command reference

### `add` — create a new prompt

```
promptvault add --command <name> --title <title> --body <text> [--tags <tag1,tag2>]
```

```powershell
promptvault add --command summarize --title "Summarize" --body "Summarize the following text." --tags "writing,productivity"
```

Omit any of `--command`/`--title`/`--body` and you'll be prompted for it
interactively. `--tags` is optional and takes a comma-separated list; tags
are created automatically if they don't already exist.

### `get` — retrieve a prompt

```
promptvault get --command <name>
```

```powershell
promptvault get --command summarize
```

If the command doesn't match exactly, PromptVault suggests similarly-named
commands (typo correction) when a close match exists.

### `list` — show every prompt

```
promptvault list
```

Prints a table of every stored prompt, with its command, title, and tags.

### `update` — change a prompt's title and/or body

```
promptvault update --command <name> [--title <new title>] [--body <new body>]
```

```powershell
promptvault update --command summarize --title "Summarize (v2)"
```

Only the fields you provide are changed; omitted fields are left as-is.

### `delete` — remove a prompt

```
promptvault delete --command <name> [--yes]
```

```powershell
promptvault delete --command summarize
promptvault delete --command summarize --yes   # skip the confirmation prompt
```

### `tag add` — apply a tag to an existing prompt

```
promptvault tag add --command <name> --tag <tag-name>
```

```powershell
promptvault tag add --command summarize --tag writing
```

### `tag remove` — remove a tag from a prompt

```
promptvault tag remove --command <name> --tag <tag-name>
```

```powershell
promptvault tag remove --command summarize --tag writing
```

### `search` — find prompts by tag

```
promptvault search --tag <tag-name>
```

```powershell
promptvault search --tag writing
```

### `--version`

```powershell
promptvault --version
```

## Running tests

```powershell
pytest
```

Tests run against an isolated, temporary SQLite database (via pytest's
`tmp_path` fixture) — your real `data\promptvault.db` is never touched.

## Development workflow

- Feature branches merge into `dev` directly.
- `dev` merges into `main` only via a GitHub Pull Request (branch protection
  on `main` blocks direct pushes).
- Pre-commit hooks (Black, Ruff, mypy, and standard hygiene checks) run on
  every commit.

```powershell
git add .
git commit -m "..."
git push -u origin <branch>
```
