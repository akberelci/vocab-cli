from typer.testing import CliRunner

from vocab import __version__
from vocab.cli import app

# CliRunner calls the app in-process and captures its output,
# so tests do not need to start a real terminal command.
runner = CliRunner()


def test_version_flag_prints_version():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"vocab {__version__}"


def test_help_lists_the_version_option():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--version" in result.output
