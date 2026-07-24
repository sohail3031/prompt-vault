# PromptVault

A personal command-line tool for storing, tagging, and instantly retrieving reusable AI prompts - no more digging
through notes apps or old chat threads to find that one prompt you know you wrote.

## Overview

I maintain dozens of reusable prompts for recurring workflows - resume vs. job description analysis, resume tailoring,
mock interview prep, project scaffolding, and more. PromptVault stores them in a local database and lets me retrieve any
prompt instantly by typing a short command (e.g. `promptvault get analyze`), or browse them by tag.

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
