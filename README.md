# PromptVault

A personal CLI and desktop tool for storing, tagging, and instantly retrieving reusable AI prompts.

## About

PromptVault is a personal tool for managing reusable AI prompts — built to
solve a simple problem: dozens of prompts for recurring workflows (resume
analysis, mock interviews, project scaffolding) scattered across notes and
old chat threads, with no fast way to find them.

It's available as both a command-line tool and a native desktop app, both
built on the same tested SQLite data layer. Store a prompt once, tag it,
and retrieve it instantly by typing a short command — no more digging.

Built end-to-end as a real-world engineering exercise: normalized schema
design, full test coverage (pytest + Click's CliRunner), proper git
branching with protected `main` and PR-based merges, pre-commit hooks
(Black, Ruff, mypy), and a packaged, standalone Windows executable via
PyInstaller.

## Tech Stack

- **Python** - core language
- **Click** - CLI framework for command structure and argument parsing
- **SQLite** - lightweight, local, file-based database (no external server required)
- **pre-commit** - automated formatyting/linting on every commit
  - **Black** - code formatting
  - **Ruff** - linting
  - Standard hygiene hooks (trailing whitespace, end-of-file fixer, large file check, merge conflict check)

## Project Status

🚧 In active development. Built in phases:

- [x] Phase 1 - Project setup & database schema
- [ ] Phase 2 - Core CRUD (add/edit/delete/list prompts)
- [ ] Phase 3 - Command lookup & tag-based search
- [ ] Phase 4 - CLI polish
- [ ] Phase 5 - Tests & documentation

## Data Model

- **`prompts`** - each prompt has a unique `command` (e.g. `analyze`), a `title`, and the prompt `body`
- **`tags`** - optional labels for browsing/searching across prompts
- **`prompt_tags`** - many-to-many join table linking prompts to tags

See [`schema.sql`](./schema.sql) for the full schema definition.

## Setup

### Prerequisites

- Python 3.x
- `sqlite3` CLI available on your PATH

### Instruction

1. Clone the repository
```bash
    git clone https://github.com/sohail3031/prompt-vault.git
    cd promptvault
```

2. Create and activate a virtual environment
```bash
  python -m venv venv
  venv\Scripts\activate    # Windows
  source venv/bin/activate # macOS/Linux
```

3. Install dependencies
```bash
  pip install -r requirements.txt
```

4. Set up pre-commit hooks
```bash
  pre-commit install
```

5. Create the local database
```bash
  sqlite3 promptvault.db < schema.sql            # macOS/Linux/cmd
  Get-Content schema.sql | sqlite promptvault.db # PowerShell
```

6. Verify the CLI works
```bash
  promptvault --help
```

## Development Workflow

- `main` - stable, production-ready code only
- `dev` - active development branch
- `feature/<short-description>` - individual feature branches off `dev`

Commits follow [Conventional Commits](https:www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, etc.)

## License

Personal project - use whatever way you want to.
