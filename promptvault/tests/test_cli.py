from __future__ import annotations

from click.testing import CliRunner

from promptvault.cli import cli

# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


def test_add_success(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            "add",
            "--command",
            "summarize",
            "--title",
            "Summarize",
            "--body",
            "Summarize this text.",
        ],
    )

    assert result.exit_code == 0
    assert "added successfully" in result.output


def test_add_duplicate_command_shows_error(runner: CliRunner):
    args = ["add", "--command", "foo", "--title", "A", "--body", "B"]
    runner.invoke(cli, args)

    result = runner.invoke(cli, args)

    assert result.exit_code == 0
    assert "already exists" in result.output


def test_add_with_tags(runner: CliRunner):
    result = runner.invoke(
        cli,
        [
            "add",
            "--command",
            "foo",
            "--title",
            "A",
            "--body",
            "B",
            "--tags",
            "career, interview",
        ],
    )

    assert result.exit_code == 0

    search_result = runner.invoke(cli, ["search", "--tag", "career"])
    assert "foo" in search_result.output


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_found(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "Title A", "--body", "B"])

    result = runner.invoke(cli, ["get", "--command", "foo"])

    assert result.exit_code == 0
    assert "Title A" in result.output


def test_get_not_found_no_suggestion(runner: CliRunner):
    result = runner.invoke(cli, ["get", "--command", "totally-unrelated-xyz"])

    assert result.exit_code == 0
    assert "no prompt" in result.output.lower()


def test_get_not_found_with_fuzzy_suggestion(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "analyze", "--title", "A", "--body", "B"])

    result = runner.invoke(cli, ["get", "--command", "analyz"])

    assert result.exit_code == 0
    assert "did you mean" in result.output.lower()
    assert "analyze" in result.output


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_output_format(runner: CliRunner):
    runner.invoke(
        cli,
        [
            "add",
            "--command",
            "foo",
            "--title",
            "Foo Title",
            "--body",
            "B",
            "--tags",
            "career",
        ],
    )

    result = runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "Foo Title" in result.output
    assert "career" in result.output


def test_list_empty(runner: CliRunner):
    result = runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "no prompts" in result.output.lower()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_confirm_accept(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "A", "--body", "B"])

    result = runner.invoke(cli, ["delete", "--command", "foo"], input="y\n")

    assert result.exit_code == 0
    assert "deleted successfully" in result.output

    get_result = runner.invoke(cli, ["get", "--command", "foo"])
    assert "no prompt" in get_result.output.lower()


def test_delete_confirm_decline(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "A", "--body", "B"])

    result = runner.invoke(cli, ["delete", "--command", "foo"], input="n\n")

    assert result.exit_code == 0

    get_result = runner.invoke(cli, ["get", "--command", "foo"])
    assert "A" in get_result.output or "foo" in get_result.output


def test_delete_with_yes_flag_skips_confirmation(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "A", "--body", "B"])

    result = runner.invoke(cli, ["delete", "--command", "foo", "--yes"])

    assert result.exit_code == 0
    assert "deleted successfully" in result.output


# ---------------------------------------------------------------------------
# tag add / tag remove
# ---------------------------------------------------------------------------


def test_tag_add_and_search(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "A", "--body", "B"])

    result = runner.invoke(cli, ["tag", "add", "--command", "foo", "--tag", "career"])

    assert result.exit_code == 0
    assert "added" in result.output.lower()

    search_result = runner.invoke(cli, ["search", "--tag", "career"])
    assert "foo" in search_result.output


def test_tag_remove(runner: CliRunner):
    runner.invoke(cli, ["add", "--command", "foo", "--title", "A", "--body", "B"])
    runner.invoke(cli, ["tag", "add", "--command", "foo", "--tag", "career"])

    result = runner.invoke(
        cli, ["tag", "remove", "--command", "foo", "--tag", "career"]
    )

    assert result.exit_code == 0
    assert "removed" in result.output.lower()

    search_result = runner.invoke(cli, ["search", "--tag", "career"])
    assert "No prompts found" in search_result.output


def test_tag_add_prompt_not_found_shows_error(runner: CliRunner):
    result = runner.invoke(cli, ["tag", "add", "--command", "ghost", "--tag", "career"])

    assert result.exit_code == 0
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_with_matches(runner: CliRunner):
    runner.invoke(
        cli,
        ["add", "--command", "foo", "--title", "A", "--body", "B", "--tags", "career"],
    )

    result = runner.invoke(cli, ["search", "--tag", "career"])

    assert result.exit_code == 0
    assert "foo" in result.output


def test_search_no_matches(runner: CliRunner):
    result = runner.invoke(cli, ["search", "--tag", "nonexistent"])

    assert result.exit_code == 0
    assert "No prompts found" in result.output


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_version_flag(runner: CliRunner):
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "version" in result.output.lower()
