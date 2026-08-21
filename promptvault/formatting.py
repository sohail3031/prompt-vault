from __future__ import annotations

from tabulate import tabulate

from promptvault.model.prompts_entry import PromptsEntry


def format_prompt_table(prompts: list[dict[str, object]]) -> str:
    """Render a list of prompts (with tags) as a formatted table.

    Args:
        prompts: A list of dicts, each with 'command', 'title', and
            'tags' keys (as returned by
            `DataOperations.list_prompts_with_tags`).

    Returns:
        A formatted table as a string, ready to print. Returns a
        plain "no prompts found" message if the list is empty.
    """
    if not prompts:
        return "No prompts found."

    rows = [
        (
            prompt["command"],
            prompt["title"],
            prompt["tags"] if prompt["tags"] else "—",
        )
        for prompt in prompts
    ]

    return tabulate(rows, headers=["Command", "Title", "Tags"], tablefmt="simple")


def format_search_results(prompts: list[PromptsEntry]) -> str:
    """Render a list of PromptsEntry search results as a formatted table.

    Args:
        prompts: A list of `PromptsEntry` objects, as returned by
            `DataOperations.search_by_tag`.

    Returns:
        A formatted table as a string, ready to print. Returns a
        plain "no prompts found" message if the list is empty.
    """
    if not prompts:
        return "No prompts found."

    rows = [(prompt.command, prompt.title) for prompt in prompts]

    return tabulate(rows, headers=["Command", "Title"], tablefmt="simple")
