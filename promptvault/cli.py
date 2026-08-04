from __future__ import annotations

import click
from promptvault.crud import DataOperations, DuplicateCommandError, InvalidCommandError
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
def add(command: str, title: str, body: str):
    """add a new prompt in the database"""
    try:
        DataOperations().add_prompt(command=command, title=title, body=body)

        click.echo(f"The prompt {command} was added successfully!")
    except DuplicateCommandError as error:
        click.echo(error)
    except InvalidCommandError as error:
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
    """get a prompt from the database"""
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
    """list all the prompts from the database"""
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
    default=None,
)
@click.option(
    "--title",
    help="Short, human-readable title for the prompt.",
    default=None,
)
@click.option("--body", help="The full prompt content to store.")
def update(command: str, title: str | None, body: str | None):
    """update the prompt in the database"""
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
    help="Short unique name used to delete this prompt .",
)
def delete(command: str):
    """delete a prompt from the database"""
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


if __name__ == "__main__":
    cli()
