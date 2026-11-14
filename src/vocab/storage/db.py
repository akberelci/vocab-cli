"""Opening the database and creating its tables."""

import sqlite3
from importlib import resources
from pathlib import Path

# Increase this when schema.sql changes. SQLite stores one integer per database
# file ("PRAGMA user_version", 0 for a new file), which we use to remember which
# schema version a file has.
SCHEMA_VERSION = 1


class DatabaseVersionError(Exception):
    """The database file was created by a newer version of vocab."""


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the database at `path`, creating the file and tables if needed.

    Pass ":memory:" for a temporary database that lives only in RAM (used in tests).
    """
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    # Rows can be read by column name (row["lemma"]) instead of by position.
    conn.row_factory = sqlite3.Row
    # SQLite ignores foreign keys unless this is switched on for each connection.
    conn.execute("PRAGMA foreign_keys = ON")

    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]

    if current == SCHEMA_VERSION:
        return
    if current > SCHEMA_VERSION:
        raise DatabaseVersionError(
            f"Database has schema version {current}, "
            f"but this version of vocab only understands up to {SCHEMA_VERSION}."
        )

    # current == 0: a brand new, empty database. Later schema versions will add
    # upgrade steps here (1 -> 2, 2 -> 3, ...).
    schema = resources.files("vocab.storage").joinpath("schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    # PRAGMA does not accept "?" parameters; the value is our own integer constant.
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
