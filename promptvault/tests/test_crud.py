from __future__ import annotations

import pytest

from promptvault.crud import (
    DataOperations,
    DuplicateCommandError,
    InvalidCommandError,
    PromptNotFoundError,
    TagAlreadyAppliedError,
)

# ---------------------------------------------------------------------------
# add_prompt
# ---------------------------------------------------------------------------


def test_add_prompt_success(data_ops: DataOperations):
    data_ops.add_prompt(command="summarize", title="Summarize", body="Summarize this.")

    prompt = data_ops.get_prompt(command="summarize")

    assert prompt is not None
    assert prompt.command == "summarize"
    assert prompt.title == "Summarize"
    assert prompt.body == "Summarize this."


def test_add_prompt_duplicate_command_raises(data_ops: DataOperations):
    data_ops.add_prompt(command="summarize", title="A", body="B")

    with pytest.raises(DuplicateCommandError):
        data_ops.add_prompt(command="summarize", title="C", body="D")


def test_add_prompt_with_tags_creates_and_links_tags(data_ops: DataOperations):
    data_ops.add_prompt(
        command="interview-prep",
        title="Interview Prep",
        body="...",
        tags=["career", "interview"],
    )

    results = data_ops.search_by_tag(tag_name="career")

    assert len(results) == 1
    assert results[0].command == "interview-prep"


def test_add_prompt_invalid_command_raises(data_ops: DataOperations):
    with pytest.raises(InvalidCommandError):
        data_ops.add_prompt(command="Invalid Command!", title="A", body="B")


def test_add_prompt_reserved_word_raises(data_ops: DataOperations):
    with pytest.raises(InvalidCommandError):
        data_ops.add_prompt(command="list", title="A", body="B")


# ---------------------------------------------------------------------------
# get_prompt
# ---------------------------------------------------------------------------


def test_get_prompt_found(data_ops: DataOperations):
    data_ops.add_prompt(command="analyze", title="Analyze", body="Analyze this.")

    prompt = data_ops.get_prompt(command="analyze")

    assert prompt is not None
    assert prompt.command == "analyze"


def test_get_prompt_not_found_returns_none(data_ops: DataOperations):
    prompt = data_ops.get_prompt(command="does-not-exist")

    assert prompt is None


# ---------------------------------------------------------------------------
# list_prompts / list_prompts_with_tags
# ---------------------------------------------------------------------------


def test_list_prompts_empty(data_ops: DataOperations):
    assert data_ops.list_prompts() == []


def test_list_prompts_single(data_ops: DataOperations):
    data_ops.add_prompt(command="one", title="One", body="Body one.")

    prompts = data_ops.list_prompts()

    assert len(prompts) == 1
    assert prompts[0].command == "one"


def test_list_prompts_many(data_ops: DataOperations):
    for i in range(3):
        data_ops.add_prompt(command=f"prompt-{i}", title=f"Title {i}", body="Body")

    prompts = data_ops.list_prompts()

    assert len(prompts) == 3


def test_list_prompts_with_tags_includes_untagged_prompts(data_ops: DataOperations):
    data_ops.add_prompt(command="tagged", title="Tagged", body="B", tags=["a"])
    data_ops.add_prompt(command="untagged", title="Untagged", body="B")

    results = data_ops.list_prompts_with_tags()
    by_command = {row["command"]: row for row in results}

    assert len(results) == 2
    assert by_command["tagged"]["tags"] == "a"
    assert by_command["untagged"]["tags"] is None


# ---------------------------------------------------------------------------
# update_prompt
# ---------------------------------------------------------------------------


def test_update_prompt_title_only(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="Old Title", body="Old Body")

    result = data_ops.update_prompt(command="foo", title="New Title", body=None)

    prompt = data_ops.get_prompt(command="foo")

    assert result is True
    assert prompt is not None
    assert prompt.title == "New Title"
    assert prompt.body == "Old Body"


def test_update_prompt_body_only(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="Old Title", body="Old Body")

    result = data_ops.update_prompt(command="foo", title=None, body="New Body")

    prompt = data_ops.get_prompt(command="foo")
    assert result is True
    assert prompt is not None
    assert prompt.title == "Old Title"
    assert prompt.body == "New Body"


def test_update_prompt_nothing_provided_returns_false(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="Old Title", body="Old Body")

    result = data_ops.update_prompt(command="foo", title=None, body=None)

    assert result is False


def test_update_prompt_not_found_returns_false(data_ops: DataOperations):
    result = data_ops.update_prompt(command="ghost", title="X", body=None)

    assert result is False


# ---------------------------------------------------------------------------
# delete_prompt
# ---------------------------------------------------------------------------


def test_delete_prompt_found(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")

    result = data_ops.delete_prompt(command="foo")

    assert result is True
    assert data_ops.get_prompt(command="foo") is None


def test_delete_prompt_not_found_returns_false(data_ops: DataOperations):
    result = data_ops.delete_prompt(command="ghost")

    assert result is False


# ---------------------------------------------------------------------------
# tags: _get_or_create_tag_id (indirectly), add_tag_to_prompt, remove_tag_from_prompt
# ---------------------------------------------------------------------------


def test_add_tag_to_prompt_creates_new_tag(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")

    data_ops.add_tag_to_prompt(command="foo", tag_name="career")

    results = data_ops.search_by_tag(tag_name="career")
    assert len(results) == 1


def test_add_tag_to_prompt_reuses_existing_tag(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")
    data_ops.add_prompt(command="bar", title="C", body="D")

    data_ops.add_tag_to_prompt(command="foo", tag_name="career")
    data_ops.add_tag_to_prompt(command="bar", tag_name="career")

    results = data_ops.search_by_tag(tag_name="career")
    assert len(results) == 2


def test_add_tag_to_prompt_duplicate_raises(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")
    data_ops.add_tag_to_prompt(command="foo", tag_name="career")

    with pytest.raises(TagAlreadyAppliedError):
        data_ops.add_tag_to_prompt(command="foo", tag_name="career")


def test_add_tag_to_prompt_missing_prompt_raises(data_ops: DataOperations):
    with pytest.raises(PromptNotFoundError):
        data_ops.add_tag_to_prompt(command="ghost", tag_name="career")


def test_remove_tag_from_prompt_success(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")
    data_ops.add_tag_to_prompt(command="foo", tag_name="career")

    result = data_ops.remove_tag_from_prompt(command="foo", tag_name="career")

    assert result is True
    assert data_ops.search_by_tag(tag_name="career") == []


def test_remove_tag_from_prompt_not_applied_returns_false(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")

    result = data_ops.remove_tag_from_prompt(command="foo", tag_name="never-applied")

    assert result is False


def test_remove_tag_from_prompt_missing_prompt_raises(data_ops: DataOperations):
    with pytest.raises(PromptNotFoundError):
        data_ops.remove_tag_from_prompt(command="ghost", tag_name="career")


# ---------------------------------------------------------------------------
# search_by_tag
# ---------------------------------------------------------------------------


def test_search_by_tag_with_matches(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B", tags=["career"])
    data_ops.add_prompt(command="bar", title="C", body="D")

    results = data_ops.search_by_tag(tag_name="career")

    assert len(results) == 1
    assert results[0].command == "foo"


def test_search_by_tag_no_matches_returns_empty_list(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")

    results = data_ops.search_by_tag(tag_name="nonexistent")

    assert results == []


def test_search_by_tag_case_and_whitespace_insensitive(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B", tags=["Career"])

    results = data_ops.search_by_tag(tag_name="  CAREER  ")

    assert len(results) == 1


# ---------------------------------------------------------------------------
# get_all_commands
# ---------------------------------------------------------------------------


def test_get_all_commands(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B")
    data_ops.add_prompt(command="bar", title="C", body="D")

    commands = data_ops.get_all_commands()

    assert sorted(commands) == ["bar", "foo"]


def test_get_all_commands_empty(data_ops: DataOperations):
    assert data_ops.get_all_commands() == []


# ---------------------------------------------------------------------------
# _validate_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "",
        "   ",
        " leading-space",
        "trailing-space ",
        "a" * 51,
        "Uppercase",
        "has spaces",
        "has_underscore",
        "-starts-with-hyphen",
        "1starts-with-digit",
        "list",
        "add",
        "delete",
    ],
)
def test_validate_command_rejects_invalid(data_ops: DataOperations, command: str):
    with pytest.raises(InvalidCommandError):
        data_ops._validate_command(command=command)


@pytest.mark.parametrize("command", ["a", "summarize", "interview-prep", "a1-b2"])
def test_validate_command_accepts_valid(data_ops: DataOperations, command: str):
    # Should not raise.
    data_ops._validate_command(command=command)


def test_delete_prompt_with_tags_succeeds(data_ops: DataOperations):
    data_ops.add_prompt(command="foo", title="A", body="B", tags=["career"])

    result = data_ops.delete_prompt(command="foo")

    assert result is True
    assert data_ops.get_prompt(command="foo") is None
