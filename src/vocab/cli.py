"""Command-line interface.

This module only defines commands and prints output. The real work lives in
the other modules, so it can be tested without going through the CLI.
"""

from typing import Annotated

import typer

from vocab import __version__

app = typer.Typer(
    help="Learn English vocabulary from real sources, with Turkish explanations.",
    no_args_is_help=True,
)


def _show_version(value: bool) -> None:
    """Print the version and stop, when --version is given."""
    if value:
        typer.echo(f"vocab {__version__}")
        raise typer.Exit()


# The callback runs before any command. For now it only carries the global
# --version option; commands (add, learn, review, stats) arrive in later milestones.
@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the version and exit.",
            callback=_show_version,
            is_eager=True,  # handle --version before anything else is checked
        ),
    ] = False,
) -> None:
    pass
