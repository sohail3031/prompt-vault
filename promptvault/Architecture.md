# Architecture

This document explains *why* PromptVault is shaped the way it is — the
schema, the class boundaries, and a few deliberate design decisions that
aren't obvious just from reading the code.

## Schema: three tables, normalized many-to-many

```
prompts  <---->  prompt_tags  <---->  tags
```

A prompt can have any number of tags, and a tag can apply to any number of
prompts — a classic many-to-many relationship. Rather than storing tags as
a comma-separated string directly on `prompts` (which would make searching
by tag slow and fragile, and duplicate tag names across rows), tags live in
their own table, and `prompt_tags` is a join table linking the two by id.

`prompt_tags` has no cascading delete behavior in the schema — deleting a
prompt requires explicitly removing its `prompt_tags` rows first, which
`delete_prompt` does within the same transaction before deleting the
prompt itself. This was a real bug caught during Phase 5 testing: SQLite's
foreign key enforcement (`PRAGMA foreign_keys = ON`) correctly rejected a
delete that would have left orphaned `prompt_tags` rows, and the fix was
to clean up the child rows explicitly rather than relying on the database
to do it automatically.

`prompts.command` and `tags.name` both have `UNIQUE` constraints, enforced
at the database level as a backstop — even though application-level
validation (`_validate_command`, tag normalization) also guards against
duplicates before a query is ever run.

## Class responsibilities

**`Database`** (`db.py`) — owns exactly one thing: producing a configured
`sqlite3.Connection` (row factory set to `sqlite3.Row`, foreign keys turned
on, timestamp parsing enabled). It also accepts an optional `db_path`
override, which exists solely so the test suite can point it at an
isolated, temporary file instead of the real database — see "Testing"
below.

**`DataOperations`** (`crud.py`) — the entire data-access layer. Every
method opens a fresh connection via `Database`, does its work, and closes
the connection before returning — no connection is held open across method
calls. This keeps each operation self-contained and avoids a whole class of
bugs around stale or leaked connections, at the cost of a small amount of
per-call overhead that's irrelevant for a single-user local CLI tool.

**`PromptsEntry`** (`model/prompts_entry.py`) — a typed dataclass
representing a prompt, with two conversion helpers: `from_row` (build a
`PromptsEntry` from a `sqlite3.Row`) and `to_db_dict` (flatten a
`PromptsEntry` back into a dict of just the columns you want to write,
filtered by an explicit `allowed_columns` list — this is what keeps
`update_prompt` from accidentally overwriting `command` or the
auto-managed timestamp columns).

## Exceptions vs. return values

PromptVault uses both, deliberately, depending on what's being signaled:

- **Exceptions** (`InvalidCommandError`, `DuplicateCommandError`,
  `PromptNotFoundError`, `TagAlreadyAppliedError`) represent conditions
  that stop an operation from completing at all — there's no sensible
  "partial" outcome to return a value for. Trying to tag a prompt that
  doesn't exist isn't a valid outcome with a boolean answer; it's an error.
- **Boolean returns** (`update_prompt`, `delete_prompt`,
  `remove_tag_from_prompt`) represent operations where "nothing happened"
  is itself a valid, expected outcome, not necessarily an error — deleting
  a prompt that's already gone, or removing a tag that was never applied,
  are things a caller might reasonably want to check without wrapping every
  call in a `try/except`.
- **`None` returns** (`get_prompt`) represent a lookup that's expected to
  sometimes come back empty — this is the most common outcome type in the
  whole class, so it stays a plain, cheap `None` check rather than an
  exception.

## The `handle_prompt_errors` decorator

Every CLI command needs to catch the same handful of exceptions
(`InvalidCommandError`, `PromptNotFoundError`, `TagAlreadyAppliedError`,
`DuplicateCommandError`, `RuntimeError`) and turn them into a clean,
one-line message instead of a raw traceback. Rather than repeating the same
`try/except` block in every command function, `handle_prompt_errors` wraps
each command once, at the decorator level:

```python
@cli.command()
@click.option(...)
@handle_prompt_errors
def some_command(...):
    ...
```

`@handle_prompt_errors` sits directly above `def`, below every
`@click.option`. This ordering matters: Click's `@click.option` decorators
attach parameter metadata onto whatever function they wrap, and
`@functools.wraps` inside `handle_prompt_errors` copies the original
function's name and docstring onto the wrapper — together, this means
Click's introspection (used for `--help` text and argument binding) still
sees the original command's signature and documentation, even though the
function it's actually calling is `handle_prompt_errors`'s inner `wrapper`.

## Testing

Tests run against an isolated, temporary SQLite database rather than the
real `data/promptvault.db`. This works via two pieces:

1. `Database.__init__` accepts an optional `db_path` override. In
   production, `DataOperations()` (no arguments) constructs a default
   `Database()`, which points at the real file. Tests instead construct
   `Database(db_path=tmp_path / "test.db")` and pass it into
   `DataOperations(database=...)`.
2. For CLI-level tests, `cli.py` always calls `DataOperations()` with no
   arguments — so a pytest fixture monkeypatches
   `promptvault.cli.DataOperations` for the duration of each test, swapping
   in a factory that returns a `DataOperations` bound to that test's
   temporary database instead.

`tests/conftest.py` holds this setup as shared fixtures (`test_db`,
`data_ops`, `runner`, and the autouse `patch_cli_data_operations`), so
individual test files just declare `data_ops`/`runner` as parameters and
get an isolated environment automatically.

`tests/test_crud.py` covers the data layer directly — every method's
success path, its failure/edge cases, and `_validate_command`'s full rule
set. `tests/test_cli.py` covers the same behavior from the outside, via
Click's `CliRunner`, catching integration issues that unit tests alone
would miss — e.g. whether `--yes` actually skips the confirmation prompt,
or whether `handle_prompt_errors` actually produces the right message when
a real command triggers it.
