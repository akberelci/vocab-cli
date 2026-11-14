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

_ITEM_COLUMNS = "id, kind, lemma, pos, zipf, status"


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


def find_item(conn: sqlite3.Connection, kind: ItemKind, lemma: str) -> Item | None:
    row = conn.execute(
        f"SELECT {_ITEM_COLUMNS} FROM items WHERE kind = ? AND lemma = ?", (kind, lemma)
    ).fetchone()
    return _row_to_item(row) if row else None


def find_items_by_lemma(conn: sqlite3.Connection, lemma: str) -> list[Item]:
    """All items with this lemma, whatever their kind (usually one, rarely two)."""
    rows = conn.execute(
        f"SELECT {_ITEM_COLUMNS} FROM items WHERE lemma = ? ORDER BY kind", (lemma,)
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def set_item_status(conn: sqlite3.Connection, item_id: int, status: ItemStatus) -> None:
    conn.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))


def list_items(conn: sqlite3.Connection, status: ItemStatus) -> list[Item]:
    """Return all items with the given status, in alphabetical order."""
    rows = conn.execute(
        f"SELECT {_ITEM_COLUMNS} FROM items WHERE status = ? ORDER BY lemma", (status,)
    ).fetchall()
    return [_row_to_item(row) for row in rows]


# Candidates are the items offered for learning: status "new", and for single
# words also rare enough. "Too easy" is not stored anywhere. It is worked out
# here from the threshold, so changing the threshold takes effect at once.
# Words without a score (zipf IS NULL) are candidates, because we cannot tell.
_WORD_CANDIDATE = "kind = 'word' AND status = 'new' AND (zipf IS NULL OR zipf < ?)"
_PHRASE_CANDIDATE = "kind != 'word' AND status = 'new'"


def list_word_candidates(
    conn: sqlite3.Connection, known_zipf: float, limit: int | None = None
) -> list[Item]:
    """Words worth learning, rarest first; words without a score come last."""
    rows = conn.execute(
        f"SELECT {_ITEM_COLUMNS} FROM items WHERE {_WORD_CANDIDATE} "
        "ORDER BY zipf IS NULL, zipf, lemma LIMIT ?",
        (known_zipf, _sql_limit(limit)),
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def count_word_candidates(conn: sqlite3.Connection, known_zipf: float) -> int:
    return conn.execute(
        f"SELECT COUNT(*) FROM items WHERE {_WORD_CANDIDATE}", (known_zipf,)
    ).fetchone()[0]


def list_phrase_candidates(conn: sqlite3.Connection, limit: int | None = None) -> list[Item]:
    """Phrasal verbs and idioms worth learning, in alphabetical order.

    Phrases are never filtered by frequency.
    """
    rows = conn.execute(
        f"SELECT {_ITEM_COLUMNS} FROM items WHERE {_PHRASE_CANDIDATE} ORDER BY lemma LIMIT ?",
        (_sql_limit(limit),),
    ).fetchall()
    return [_row_to_item(row) for row in rows]


def count_phrase_candidates(conn: sqlite3.Connection) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM items WHERE {_PHRASE_CANDIDATE}").fetchone()[0]


def _sql_limit(limit: int | None) -> int:
    return -1 if limit is None else limit  # in SQLite, LIMIT -1 means "no limit"


def count_items(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]


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
