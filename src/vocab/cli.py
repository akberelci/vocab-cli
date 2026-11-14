"""Command-line interface.

This module only defines commands and prints output. The real work lives in
the other modules, so it can be tested without going through the CLI.
"""

import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from vocab import __version__, config, importer, known
from vocab.models import Item, ItemKind
from vocab.nlp.examples import best_example
from vocab.sources.text_file import SourceError, read_text_file
from vocab.storage import db, repo

app = typer.Typer(
    help="Learn English vocabulary from real sources, with Turkish explanations.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Show or change settings.", invoke_without_command=True)
app.add_typer(config_app, name="config")

_KIND_LABELS = {
    ItemKind.WORD: "word",
    ItemKind.PHRASAL_VERB: "phrasal verb",
    ItemKind.IDIOM: "idiom",
}


def _show_version(value: bool) -> None:
    """Print the version and stop, when --version is given."""
    if value:
        typer.echo(f"vocab {__version__}")
        raise typer.Exit()


# The callback runs before any command. It only carries the global --version option.
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


# --- helpers ------------------------------------------------------------------


def _fail(message: str) -> typer.Exit:
    """Print an error and return the exception that ends the command with exit code 1."""
    typer.echo(f"Error: {message}", err=True)
    return typer.Exit(code=1)


def _load_config() -> config.Config:
    """Read the settings; on the first run, say where the new file was created."""
    try:
        settings, created = config.load()
    except config.ConfigError as error:
        raise _fail(str(error)) from None
    if created:
        typer.echo(f"Created settings file: {config.config_path()}")
    return settings


def _open_database() -> sqlite3.Connection:
    path = config.database_path()
    is_new = not path.exists()
    conn = db.connect(path)
    if is_new:
        typer.echo(f"Created database: {path}")
    return conn


# --- vocab add ----------------------------------------------------------------


@app.command()
def add(
    path: Annotated[Path, typer.Argument(help="A plain text file (UTF-8).")],
) -> None:
    """Import a text and extract the words and phrases worth learning."""
    settings = _load_config()
    conn = _open_database()

    try:
        source = read_text_file(path)
        result = importer.import_source(conn, source, settings.known_zipf)
    except SourceError as error:
        raise _fail(str(error)) from None
    except importer.AlreadyImportedError:
        typer.echo("This text was already imported. Nothing was changed.")
        return
    finally:
        conn.close()

    typer.echo(f'Imported "{source.title}": {result.total} different words and phrases')
    typer.echo("")
    _summary_row("  New candidates", result.new_candidates)
    _summary_row("    words", result.new_words)
    _summary_row("    phrasal verbs", result.new_phrasal_verbs)
    _summary_row("    idioms", result.new_idioms)
    typer.echo("  Skipped")
    _summary_row(f"    too easy (Zipf >= {settings.known_zipf:g})", result.too_easy)
    _summary_row("    marked known or ignored", result.known_or_ignored)
    _summary_row("  Seen in earlier imports", result.seen_before)
    if result.unscored:
        typer.echo("")
        typer.echo(
            f"  {result.unscored} of the new words are not in the frequency list "
            "(very rare words, typos or names)."
        )
    typer.echo("")
    typer.echo("Run `vocab list` to see the candidates.")


def _summary_row(label: str, count: int) -> None:
    typer.echo(f"{label:<30}{count:>5}")


# --- vocab list ---------------------------------------------------------------


@app.command("list")
def list_candidates(
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, help="Rows to show in each section.")
    ] = 20,
) -> None:
    """Show the candidates: rare words first, then phrasal verbs and idioms."""
    settings = _load_config()
    conn = _open_database()

    try:
        words = repo.list_word_candidates(conn, settings.known_zipf, limit)
        word_total = repo.count_word_candidates(conn, settings.known_zipf)
        phrases = repo.list_phrase_candidates(conn, limit)
        phrase_total = repo.count_phrase_candidates(conn)

        if word_total + phrase_total == 0:
            typer.echo("No candidates yet. Import a text with `vocab add <file>`.")
            return

        _print_section(
            conn, f"Words below Zipf {settings.known_zipf:g}, rarest first", words, word_total
        )
        typer.echo("")
        _print_section(conn, "Phrasal verbs and idioms", phrases, phrase_total)
    finally:
        conn.close()


def _print_section(conn: sqlite3.Connection, title: str, items: list[Item], total: int) -> None:
    shown = f"{total}" if len(items) == total else f"showing {len(items)} of {total}"
    typer.echo(f"{title} ({shown})")
    typer.echo(f"  {'ZIPF':>4}  {'TYPE':<12}  ITEM / EXAMPLE")

    for item in items:
        zipf = "-" if item.kind is not ItemKind.WORD else _format_zipf(item.zipf)
        typer.echo(f"  {zipf:>4}  {_KIND_LABELS[item.kind]:<12}  {item.lemma}")
        example = best_example(repo.list_occurrences(conn, item.id))
        if example:
            typer.echo(f"  {'':>4}  {'':<12}    {example.sentence}")

    if len(items) < total:
        typer.echo(f"  ... {total - len(items)} more. Use --limit to see more.")


def _format_zipf(zipf: float | None) -> str:
    return "?" if zipf is None else f"{zipf:.2f}"


# --- vocab known --------------------------------------------------------------

_KNOWN_MESSAGES = {
    known.Outcome.MARKED: "marked as known",
    known.Outcome.CREATED: "added as a known word",
    known.Outcome.ALREADY: "nothing to change",
    known.Outcome.UNMARKED: "no longer marked as known",
    known.Outcome.NOT_FOUND: "not found",
}


@app.command("known")
def mark_known(
    items: Annotated[
        list[str],
        typer.Argument(
            help='Words or phrases in their base form. Put phrases in quotes: "give up".'
        ),
    ],
    undo: Annotated[bool, typer.Option("--undo", help="Remove the known mark again.")] = False,
) -> None:
    """Mark words or phrases as known, so they are no longer offered."""
    _load_config()
    conn = _open_database()

    not_found = False
    try:
        with conn:  # all marks are saved together
            for text in items:
                change = known.unmark_known if undo else known.mark_known
                outcome = change(conn, text)
                not_found = not_found or outcome is known.Outcome.NOT_FOUND
                typer.echo(f"  {text}: {_KNOWN_MESSAGES[outcome]}")
    finally:
        conn.close()

    if not_found:
        typer.echo("")
        typer.echo(
            "Items that were not found: use the base form shown by `vocab list` "
            '("give up", not "gave up"). Phrases must have been found in a text first.'
        )
        raise typer.Exit(code=1)


# --- vocab config -------------------------------------------------------------


@config_app.callback()
def config_show(ctx: typer.Context) -> None:
    """Show the settings and where vocab keeps its files."""
    if ctx.invoked_subcommand is not None:
        return
    settings = _load_config()
    typer.echo(f"Settings file: {config.config_path()}")
    typer.echo(f"Database:      {config.database_path()}")
    typer.echo("")
    typer.echo(f"known_zipf = {settings.known_zipf:g}")
    typer.echo("  Words with a Zipf score at or above this count as known.")
    typer.echo("  Change it with: vocab config known-zipf 3.8")


@config_app.command("known-zipf")
def config_known_zipf(
    value: Annotated[float, typer.Argument(help="New threshold, e.g. 4.0 for B2.")],
) -> None:
    """Set the frequency threshold above which words count as known."""
    _load_config()  # creates the file on a first run and checks that it is readable
    try:
        new_value = config.validate_known_zipf(value)
    except config.ConfigError as error:
        raise _fail(str(error)) from None

    config.save(config.Config(known_zipf=new_value))
    typer.echo(f"known_zipf = {new_value:g}")
