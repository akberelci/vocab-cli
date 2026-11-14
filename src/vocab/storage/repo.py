"""All SQL queries live here, so no other module needs to know the table layout.

These functions do not commit. The caller decides what belongs together:

    with conn:                      # commits at the end, rolls back on an error
        source_id = repo.add_source(conn, ...)
        item_id = repo.upsert_item(conn, ...)

That way one import is saved completely or not at all.

Functions for cards and reviews are added in the milestones that need them.
"""

import sqlite3
from datetime import UTC, datetime

from vocab.models import Item, ItemKind, ItemStatus, Occurrence, SourceKind


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- sources -----------------------------------------------------------------


def add_source(
    conn: sqlite3.Connection,
    kind: SourceKind,
    ref: str,
    title: str | None,
    content_hash: str,
) -> int:
    """Save an imported source and return its id.

    Raises sqlite3.IntegrityError if a source with the same content already exists.
    """
    cursor = conn.execute(
        "INSERT INTO sources (kind, ref, title, content_hash, added_at) VALUES (?, ?, ?, ?, ?)",
        (kind, ref, title, content_hash, _now()),
    )
    return cursor.lastrowid


def find_source_by_hash(conn: sqlite3.Connection, content_hash: str) -> int | None:
    """Return the id of the source with this content, or None if it is new."""
    row = conn.execute("SELECT id FROM sources WHERE content_hash = ?", (content_hash,)).fetchone()
    return row["id"] if row else None


# --- items -------------------------------------------------------------------


def upsert_item(
    conn: sqlite3.Connection,
    kind: ItemKind,
    lemma: str,
    pos: str | None = None,
    zipf: float | None = None,
) -> int:
    """Return the id of the item (kind, lemma), creating it if it does not exist.

    An existing item is left untouched, so its status (e.g. "known") survives
    when the same word shows up again in a later import.
    """
    conn.execute(
        "INSERT INTO items (kind, lemma, pos, zipf, created_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (kind, lemma) DO NOTHING",
        (kind, lemma, pos, zipf, _now()),
    )
    row = conn.execute(
        "SELECT id FROM items WHERE kind = ? AND lemma = ?", (kind, lemma)
    ).fetchone()
    return row["id"]


def set_item_status(conn: sqlite3.Connection, item_id: int, status: ItemStatus) -> None:
    conn.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))


def list_items(conn: sqlite3.Connection, status: ItemStatus) -> list[Item]:
    """Return all items with the given status, in alphabetical order."""
    rows = conn.execute(
        "SELECT id, kind, lemma, pos, zipf, status FROM items WHERE status = ? ORDER BY lemma",
        (status,),
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def _row_to_item(row: sqlite3.Row) -> Item:
    return Item(
        id=row["id"],
        kind=ItemKind(row["kind"]),
        lemma=row["lemma"],
        pos=row["pos"],
        zipf=row["zipf"],
        status=ItemStatus(row["status"]),
    )


# --- occurrences -------------------------------------------------------------


def add_occurrence(
    conn: sqlite3.Connection,
    item_id: int,
    source_id: int,
    sentence: str,
    surface_form: str,
) -> None:
    """Record that an item was seen in a sentence of a source.

    The same sentence is stored only once per item and source.
    """
    conn.execute(
        "INSERT OR IGNORE INTO occurrences (item_id, source_id, sentence, surface_form) "
        "VALUES (?, ?, ?, ?)",
        (item_id, source_id, sentence, surface_form),
    )


def list_occurrences(conn: sqlite3.Connection, item_id: int) -> list[Occurrence]:
    """Return the sentences an item was seen in, oldest first."""
    rows = conn.execute(
        "SELECT sentence, surface_form FROM occurrences WHERE item_id = ? ORDER BY id",
        (item_id,),
    ).fetchall()
    return [Occurrence(sentence=row["sentence"], surface_form=row["surface_form"]) for row in rows]
