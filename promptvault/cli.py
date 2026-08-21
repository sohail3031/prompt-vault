from __future__ import annotations

import functools
import difflib
import click

from promptvault.crud import (
    DataOperations,
    DuplicateCommandError,
    InvalidCommandError,
    PromptNotFoundError,
    TagAlreadyAppliedError,
)
from promptvault.formatting import format_prompt_table, format_search_results


def handle_prompt_errors(func):
    """Catch and cleanly report known PromptVault exceptions.

    Wraps a Click command function so that any of the known,
    user-facing exceptions raised by the data layer are caught and
    printed as a clean message instead of propagating as a raw
    traceback.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (
            InvalidCommandError,
            PromptNotFoundError,
            TagAlreadyAppliedError,
            DuplicateCommandError,
            RuntimeError,
        ) as error:
            click.echo(f"Error: {error}")

    return wrapper


@click.group()
@click.version_option()
def cli():
    """PromptVault — store, tag, and retrieve reusable AI prompts."""
    pass


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="Short, unique name used to look up this prompt later (letters, digits, hyphens).",
)
@click.option(
    "--title", prompt="Title", help="Short, human-readable title for the prompt."
)
@click.option("--body", prompt="Prompt text", help="The full prompt content to store.")
@click.option(
    "--tags",
    default=None,
    help="Optional comma-separated tags to apply, e.g. 'interview,career'.",
)
@handle_prompt_errors
def add(command: str, title: str, body: str, tags: str | None):
    """Add a new prompt to the database, optionally tagging it.

    Args:
        command: Unique name used to look up this prompt later.
        title: Short, human-readable title for the prompt.
        body: The full prompt content to store.
        tags: Optional comma-separated tag names (e.g. 'interview,career').
            Tags are created automatically if they don't already exist.
    """
    tag_list: list[str] | None = None

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t]

    DataOperations().add_prompt(command=command, title=title, body=body, tags=tag_list)

    click.echo(f"The prompt {command} was added successfully!")


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="The command name of the prompt to retrieve.",
)
@handle_prompt_errors
def get(command: str):
    """Look up and display a prompt by its command name.

    If no exact match is found, suggests similarly-named commands
    as a typo-correction hint.

    Args:
        command: The unique command name identifying the prompt.
    """
    prompt = DataOperations().get_prompt(command=command)

    if prompt:
        click.echo(f"{prompt.command}\n{prompt.title}\n{prompt.body}")
        return

    all_commands = DataOperations().get_all_commands()
    suggestions = difflib.get_close_matches(command, all_commands, n=3, cutoff=0.6)

    if suggestions:
        click.echo(
            f"No prompt found for '{command}'. Did you mean: "
            f"{', '.join(suggestions)}?"
        )
    else:
        click.echo(f"There is no prompt with {command}")


@cli.command(name="list")
@handle_prompt_errors
def list_prompts():
    """List every prompt in the database, along with its tags."""
    available_prompts = DataOperations().list_prompts_with_tags()
    click.echo(format_prompt_table(available_prompts))


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="The command name of the prompt to update.",
)
@click.option(
    "--title",
    default=None,
    help="New title for the prompt. Omit to leave the title unchanged.",
)
@click.option(
    "--body",
    default=None,
    help="New prompt text. Omit to leave the body unchanged.",
)
@handle_prompt_errors
def update(command: str, title: str | None, body: str | None):
    """Update an existing prompt's title and/or body.

    Only the fields explicitly provided are changed; omitting --title
    or --body leaves that field unchanged. If neither is provided,
    nothing is updated.

    Args:
        command: The unique command name identifying the prompt to
            update.
        title: New title for the prompt, or omit to leave unchanged.
        body: New body text for the prompt, or omit to leave unchanged.
    """
    flag = DataOperations().update_prompt(command=command, title=title, body=body)

    if flag:
        click.echo(f"The prompt with {command} has been updated successfully.")
    else:
        click.echo(f"Unable to update the prompt with {command}.")


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="The command name of the prompt to delete.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip the confirmation prompt and delete immediately.",
)
@handle_prompt_errors
def delete(command: str, yes: bool):
    """Delete a prompt from the database, after confirming with the user.

    Args:
        command: The unique command name identifying the prompt to
            delete.
        yes: If True, skip the confirmation prompt and delete
            immediately without asking.
    """
    if not yes and not click.confirm(f"Delete prompt '{command}'?"):
        return

    flag = DataOperations().delete_prompt(command=command)

    if flag:
        click.echo(f"The prompt with {command} has been deleted successfully.")
    else:
        click.echo(f"Unable to delete the prompt with {command}.")


@cli.group()
def tag():
    """Add or remove tags on an existing prompt."""
    pass


@tag.command(name="add")
@click.option(
    "--command",
    prompt=True,
    help="The command name of the prompt to tag.",
)
@click.option(
    "--tag",
    "tag_name",
    prompt=True,
    help="The tag name to apply. Created automatically if it doesn't exist.",
)
@handle_prompt_errors
def tag_add(command: str, tag_name: str):
    """Apply a tag to an existing prompt, creating the tag if needed.

    Args:
        command: The unique command name identifying the prompt to tag.
        tag_name: The tag name to apply. Tags are matched case- and
            whitespace-insensitively, and created automatically if
            they don't already exist.
    """
    DataOperations().add_tag_to_prompt(command=command, tag_name=tag_name)
    click.echo(f"Tag '{tag_name}' added to {command}.")


@tag.command(name="remove")
@click.option(
    "--command",
    prompt=True,
    help="The command name of the prompt to untag.",
)
@click.option(
    "--tag",
    "tag_name",
    prompt=True,
    help="The tag name to remove from the prompt.",
)
@handle_prompt_errors
def tag_remove(command: str, tag_name: str):
    """Remove a tag from a prompt, if it's currently applied.

    Args:
        command: The unique command name identifying the prompt.
        tag_name: The tag name to remove from the prompt.
    """
    flag = DataOperations().remove_tag_from_prompt(command=command, tag_name=tag_name)

    if flag:
        click.echo(f"The tag '{tag_name}' was removed from {command}.")
    else:
        click.echo(
            f"The tag '{tag_name}' was not applied to {command} (or doesn't exist)."
        )


@cli.command()
@click.option(
    "--tag",
    "tag_name",
    prompt=True,
    help="The tag name to search for.",
)
@handle_prompt_errors
def search(tag_name: str):
    """Search for prompts by tag name.

    Args:
        tag_name: The tag name to search for. Matching is case- and
            whitespace-insensitive.
    """
    results = DataOperations().search_by_tag(tag_name=tag_name)
    click.echo(format_search_results(results))


if __name__ == "__main__":
    cli()
