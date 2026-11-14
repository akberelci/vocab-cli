"""Marking items as known by hand, and undoing it.

Items you mark are stored with status "known". This is separate from "too
easy", which is never stored: that is worked out from the frequency threshold.
"""

import sqlite3
from enum import Enum

from vocab import difficulty
from vocab.models import ItemKind, ItemStatus
from vocab.storage import repo


class Outcome(Enum):
    MARKED = "marked"  # an existing item is now known
    CREATED = "created"  # the word was not in the database yet; added as known
    ALREADY = "already"  # nothing to change
    UNMARKED = "unmarked"  # a known item is a candidate again
    NOT_FOUND = "not_found"


def mark_known(conn: sqlite3.Connection, text: str) -> Outcome:
    """Mark a word or phrase (given in its base form) as known."""
    lemma = _normalise(text)
    items = repo.find_items_by_lemma(conn, lemma)

    if not items:
        # A phrase we have never seen: we cannot know whether it is a phrasal
        # verb or an idiom, or whether it is spelled the way the tool would
        # store it. A single word is safe to add, so later imports skip it.
        if " " in lemma or not lemma:
            return Outcome.NOT_FOUND
        item_id = repo.upsert_item(conn, ItemKind.WORD, lemma, zipf=difficulty.zipf_score(lemma))
        repo.set_item_status(conn, item_id, ItemStatus.KNOWN)
        return Outcome.CREATED

    to_change = [item for item in items if item.status is not ItemStatus.KNOWN]
    for item in to_change:
        repo.set_item_status(conn, item.id, ItemStatus.KNOWN)
    return Outcome.MARKED if to_change else Outcome.ALREADY


def unmark_known(conn: sqlite3.Connection, text: str) -> Outcome:
    """Undo mark_known: the item becomes a normal new item again."""
    items = repo.find_items_by_lemma(conn, _normalise(text))
    if not items:
        return Outcome.NOT_FOUND

    known = [item for item in items if item.status is ItemStatus.KNOWN]
    for item in known:
        repo.set_item_status(conn, item.id, ItemStatus.NEW)
    return Outcome.UNMARKED if known else Outcome.ALREADY


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())
