from __future__ import annotations

from typing import Optional

import click
from promptvault.crud import (
    DataOperations,
    DuplicateCommandError,
    InvalidCommandError,
    TagAlreadyAppliedError,
    PromptNotFoundError,
)
from promptvault.model.prompts_entry import PromptsEntry


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="Short unique name used to look up this prompt later.",
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
def add(command: str, title: str, body: str, tags: Optional[str]):
    """Add a new prompt to the database, optionally tagging it.

    Args:
        command: Unique name used to look up this prompt later.
        title: Short, human-readable title for the prompt.
        body: The full prompt content to store.
        tags: Optional comma-separated tag names (e.g. 'interview,career').
            Tags are created automatically if they don't already exist.
    """
    try:
        tag_list: Optional[list[str]] = None

        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t]

        DataOperations().add_prompt(
            command=command, title=title, body=body, tags=tag_list
        )

        click.echo(f"The prompt {command} was added successfully!")
    except DuplicateCommandError as error:
        click.echo(error)
    except InvalidCommandError as error:
        click.echo(error)
    except TagAlreadyAppliedError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="Short unique name used to get this prompt later.",
)
def get(command: str):
    """Retrieve and display a single prompt by its command name.

    Args:
        command: The unique command name identifying the prompt.
    """
    try:
        prompt: PromptsEntry | None = DataOperations().get_prompt(command=command)

        if prompt:
            click.echo(f"{prompt.command}\n{prompt.title}\n{prompt.body}")
        else:
            click.echo(f"There is not prompt with {command}")
    except InvalidCommandError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@cli.command(name="list")
def list_prompts():
    """List every prompt currently stored in the database."""
    try:
        available_prompts: list[PromptsEntry] = DataOperations().list_prompts()

        for prompt in available_prompts:
            click.echo(f"{prompt.command}\n{prompt.title}\n{prompt.body}")
    except RuntimeError as error:
        click.echo(error)


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="Short unique name used to update this prompt later.",
)
@click.option(
    "--title",
    help="Short, human-readable title for the prompt.",
    default=None,
)
@click.option("--body", help="The full prompt content to store.")
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
    try:
        flag: bool = DataOperations().update_prompt(
            command=command, title=title, body=body
        )

        if flag:
            click.echo(f"The prompt with {command} has been updated successfully.")
        else:
            click.echo(f"Unable to update the prompt with {command}.")
    except InvalidCommandError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@cli.command()
@click.option(
    "--command",
    prompt="Command name (e.g. 'summarize')",
    help="Short unique name used to delete this prompt.",
)
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
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

    try:
        flag: bool = DataOperations().delete_prompt(command=command)

        if flag:
            click.echo(f"The prompt with {command} has been deleted successfully.")
        else:
            click.echo(f"Unable to delete the prompt with {command}.")
    except InvalidCommandError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@cli.group()
def tag():
    pass


@tag.command(name="add")
@click.option("--command", prompt=True, help="Name of the Prompt to add")
@click.option("--tag", "tag_name", prompt=True, help="Name of the Tag to add")
def tag_add(command: str, tag_name: str):
    """Apply a tag to an existing prompt, creating the tag if needed.

    Args:
        command: The unique command name identifying the prompt to tag.
        tag_name: The tag name to apply. Tags are matched case- and
            whitespace-insensitively, and created automatically if
            they don't already exist.
    """
    try:
        DataOperations().add_tag_to_prompt(command=command, tag_name=tag_name)

        click.echo(
            f"Tag: '{tag_name}' has been added to the Prompt: '{command}' successfully."
        )
    except InvalidCommandError as error:
        click.echo(error)
    except PromptNotFoundError as error:
        click.echo(error)
    except TagAlreadyAppliedError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@tag.command(name="remove")
@click.option("--command", prompt=True, help="Name of the Prompt to remove")
@click.option("--tag", "tag_name", prompt=True, help="Name of Tag to remove")
def tag_remove(command: str, tag_name: str):
    """Remove a tag from a prompt, if it's currently applied.

    Args:
        command: The unique command name identifying the prompt.
        tag_name: The tag name to remove from the prompt.
    """
    try:
        flag: bool = DataOperations().remove_tag_from_prompt(
            command=command, tag_name=tag_name
        )

        if flag:
            click.echo(f"The tag '{tag_name}' was removed from {command}.")
        else:
            click.echo(
                f"The tag '{tag_name}' was not applied to {command} (or doesn't exist)."
            )
    except InvalidCommandError as error:
        click.echo(error)
    except PromptNotFoundError as error:
        click.echo(error)
    except RuntimeError as error:
        click.echo(error)


@cli.command()
@click.option("--tag", "tag_name", prompt=True, help="Find prompts by tag")
def search(tag_name: str):
    """Search for prompts by tag name.

    Args:
        tag_name: The tag name to search for. Matching is case- and
            whitespace-insensitive.
    """
    try:
        results = DataOperations().search_by_tag(tag_name=tag_name)

        if not results:
            click.echo(f"No prompts found with tag: '{tag_name}'.")
        else:
            for prompt in results:
                click.echo(f"{prompt.command}\n{prompt.title}")
    except RuntimeError as error:
        click.echo(error)


if __name__ == "__main__":
    cli()
