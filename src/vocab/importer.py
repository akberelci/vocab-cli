"""Importing a source: text in, items and occurrences saved.

This module connects the pieces (language processing and storage) and is what
the `vocab add` command will call. It does not print anything itself.
"""

import sqlite3
from dataclasses import dataclass

from vocab.nlp import pipeline, words
from vocab.sources.base import SourceText
from vocab.storage import repo


class AlreadyImportedError(Exception):
    """A source with exactly the same text was imported before."""


@dataclass(frozen=True)
class ImportResult:
    source_id: int
    candidates: int  # how many words were found in the text, counting repeats
    new_items: int  # how many of them were not in the database before


def import_source(conn: sqlite3.Connection, source: SourceText) -> ImportResult:
    """Extract the words of a source and save them with their example sentences."""
    if repo.find_source_by_hash(conn, source.content_hash) is not None:
        raise AlreadyImportedError(f"This text was already imported: {source.ref}")

    # The slow part (running spaCy) happens before the database is touched.
    candidates = list(words.extract_words(pipeline.parse(source.text)))

    # One transaction: if anything fails, nothing of this import is saved.
    with conn:
        items_before = repo.count_items(conn)
        source_id = repo.add_source(
            conn, source.kind, source.ref, source.title, source.content_hash
        )
        for candidate in candidates:
            item_id = repo.upsert_item(conn, candidate.kind, candidate.lemma, pos=candidate.pos)
            repo.add_occurrence(
                conn, item_id, source_id, candidate.sentence, candidate.surface_form
            )
        new_items = repo.count_items(conn) - items_before

    return ImportResult(source_id=source_id, candidates=len(candidates), new_items=new_items)
