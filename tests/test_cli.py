"""The commands, run in-process against temporary settings and data folders
(see the autouse fixture in conftest.py)."""

import pytest
from typer.testing import CliRunner

from vocab import __version__, config
from vocab.cli import app

# CliRunner calls the app in-process and captures its output,
# so tests do not need to start a real terminal command.
runner = CliRunner()

STORY = (
    "At first, the reluctant athlete couldn't keep up with the others.\n"
    "She nearly gave up, but Tom told her it was worthwhile.\n"
)


@pytest.fixture
def story(tmp_path):
    path = tmp_path / "story.txt"
    path.write_text(STORY, encoding="utf-8")
    return path


def run(*arguments):
    return runner.invoke(app, [str(argument) for argument in arguments])


# --- basics --------------------------------------------------------------------


def test_version_flag_prints_version():
    result = run("--version")

    assert result.exit_code == 0
    assert result.output.strip() == f"vocab {__version__}"


def test_help_lists_the_commands():
    result = run("--help")

    assert result.exit_code == 0
    for command in ("add", "list", "known", "config"):
        assert command in result.output


# --- first run -----------------------------------------------------------------


def test_first_command_creates_settings_and_database_and_says_where(story):
    result = run("add", story)

    assert result.exit_code == 0
    assert f"Created settings file: {config.config_path()}" in result.output
    assert f"Created database: {config.database_path()}" in result.output
    assert config.config_path().exists()
    assert config.database_path().exists()


def test_later_commands_do_not_repeat_the_first_run_messages(story):
    run("add", story)

    result = run("list")

    assert "Created" not in result.output


# --- vocab add -------------------------------------------------------------------


def test_add_prints_a_summary(story):
    result = run("add", story)

    assert result.exit_code == 0
    lines = [" ".join(line.split()) for line in result.output.splitlines()]
    assert 'Imported "story": 18 different words and phrases' in lines
    assert "New candidates 5" in lines
    assert "words 2" in lines  # reluctant, worthwhile
    assert "phrasal verbs 2" in lines  # keep up with, give up
    assert "idioms 1" in lines  # at first
    assert "too easy (Zipf >= 4) 13" in lines
    assert "marked known or ignored 0" in lines
    assert "Seen in earlier imports 0" in lines


def test_add_the_same_text_twice_changes_nothing(story):
    run("add", story)

    result = run("add", story)

    assert result.exit_code == 0
    assert "already imported" in result.output
    assert "New candidates" not in result.output


def test_add_missing_file_fails_with_a_readable_message(tmp_path):
    result = run("add", tmp_path / "missing.txt")

    assert result.exit_code == 1
    assert "Error: File not found" in result.output


def test_add_mentions_words_missing_from_the_frequency_list(tmp_path):
    path = tmp_path / "odd.txt"
    path.write_text("The machine began to zxqvorble loudly.", encoding="utf-8")

    result = run("add", path)

    assert "1 of the new words are not in the frequency list" in result.output


def test_add_uses_the_threshold_from_the_settings(story):
    run("config", "known-zipf", "4.5")

    result = run("add", story)

    lines = [" ".join(line.split()) for line in result.output.splitlines()]
    assert "words 3" in lines  # athlete (4.11) is now a candidate too
    assert "too easy (Zipf >= 4.5) 12" in lines


# --- vocab list ------------------------------------------------------------------


def test_list_without_imports_explains_what_to_do():
    result = run("list")

    assert result.exit_code == 0
    assert "No candidates yet" in result.output


def test_list_shows_words_rarest_first_with_type_score_and_example(story):
    run("add", story)

    result = run("list")

    assert result.exit_code == 0
    output = result.output
    assert "Words below Zipf 4, rarest first (2)" in output
    assert output.index("worthwhile") < output.index("3.81  word          reluctant")
    assert "3.74  word          worthwhile" in output
    assert "She nearly gave up, but Tom told her it was worthwhile." in output


def test_list_shows_phrases_in_their_own_section_without_a_score(story):
    run("add", story)

    output = run("list").output

    phrases = output[output.index("Phrasal verbs and idioms (3)") :]
    assert "   -  idiom         at first" in phrases
    assert "   -  phrasal verb  give up" in phrases
    assert "   -  phrasal verb  keep up with" in phrases
    assert "reluctant" not in phrases.replace("the reluctant athlete", "")


def test_list_limit_applies_to_each_section(story):
    run("add", story)

    output = run("list", "--limit", "1").output

    assert "(showing 1 of 2)" in output
    assert "(showing 1 of 3)" in output
    assert "... 1 more. Use --limit to see more." in output
    assert "... 2 more. Use --limit to see more." in output
    assert "3.81" not in output  # the second word is cut off


def test_list_follows_a_changed_threshold_without_a_new_import(story):
    run("add", story)
    run("config", "known-zipf", "4.5")

    output = run("list").output

    assert "Words below Zipf 4.5, rarest first (3)" in output
    assert "athlete" in output


# --- vocab known -----------------------------------------------------------------


def test_known_removes_items_from_the_list(story):
    run("add", story)

    result = run("known", "reluctant", "give up")

    assert result.exit_code == 0
    assert "reluctant: marked as known" in result.output
    assert "give up: marked as known" in result.output
    output = run("list").output
    assert "word          reluctant" not in output
    assert "phrasal verb  give up" not in output
    assert "worthwhile" in output


def test_known_undo_brings_the_item_back(story):
    run("add", story)
    run("known", "reluctant")

    result = run("known", "--undo", "reluctant")

    assert "reluctant: no longer marked as known" in result.output
    assert "word          reluctant" in run("list").output


def test_known_word_is_skipped_by_a_later_import(story):
    run("known", "reluctant")

    result = run("add", story)

    lines = [" ".join(line.split()) for line in result.output.splitlines()]
    assert "words 1" in lines  # only worthwhile
    assert "marked known or ignored 1" in lines


def test_known_reports_what_it_cannot_find(story):
    run("add", story)

    result = run("known", "reluctant", "gave up")

    assert result.exit_code == 1
    assert "reluctant: marked as known" in result.output
    assert "gave up: not found" in result.output
    assert "base form" in result.output


# --- vocab config ----------------------------------------------------------------


def test_config_shows_paths_and_the_current_value():
    result = run("config")

    assert result.exit_code == 0
    assert str(config.config_path()) in result.output
    assert str(config.database_path()) in result.output
    assert "known_zipf = 4" in result.output


def test_config_changes_the_threshold():
    result = run("config", "known-zipf", "3.8")

    assert result.exit_code == 0
    assert "known_zipf = 3.8" in result.output
    assert config.load()[0].known_zipf == 3.8


def test_config_refuses_a_value_outside_the_scale():
    result = run("config", "known-zipf", "12")

    assert result.exit_code == 1
    assert "between 0 and 8" in result.output
    assert config.load()[0].known_zipf == 4.0


def test_broken_settings_file_gives_a_readable_error(story):
    config.config_path().parent.mkdir(parents=True)
    config.config_path().write_text('known_zipf = "high"\n', encoding="utf-8")

    result = run("add", story)

    assert result.exit_code == 1
    assert "Error: known_zipf must be a number" in result.output
