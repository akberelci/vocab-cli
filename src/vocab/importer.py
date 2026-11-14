"""Importing a source: text in, items and occurrences saved.

This module connects the pieces (language processing, difficulty and storage)
and is what the `vocab add` command calls. It does not print anything itself.
"""

import sqlite3
from dataclasses import dataclass

from vocab import difficulty
from vocab.models import Candidate, Item, ItemKind, ItemStatus
from vocab.nlp import cleaning, extract, pipeline
from vocab.sources.base import SourceText
from vocab.storage import repo


class AlreadyImportedError(Exception):
    """A source with exactly the same text was imported before."""


@dataclass(frozen=True)
class ImportResult:
    """What an import found. Every count is in distinct items, not repeats,
    and every item of the text is counted in exactly one of the groups."""

    source_id: int

    # New candidates: seen for the first time and worth learning.
    new_words: int = 0
    new_phrasal_verbs: int = 0
    new_idioms: int = 0

    # Not offered for learning.
    too_easy: int = 0  # words at or above the frequency threshold
    known_or_ignored: int = 0  # marked by the user

    # Already candidates or being learned because of an earlier import.
    seen_before: int = 0

    # How many of new_words have no frequency score (wordfreq does not know them).
    unscored: int = 0

    @property
    def new_candidates(self) -> int:
        return self.new_words + self.new_phrasal_verbs + self.new_idioms

    @property
    def total(self) -> int:
        return self.new_candidates + self.too_easy + self.known_or_ignored + self.seen_before


def import_source(conn: sqlite3.Connection, source: SourceText, known_zipf: float) -> ImportResult:
    """Extract the words and phrases of a source and save them with their example sentences.

    `known_zipf` is only used to count what is too easy. Everything is saved
    either way, so a different threshold later still has all the data.
    """
    if repo.find_source_by_hash(conn, source.content_hash) is not None:
        raise AlreadyImportedError(f"This text was already imported: {source.ref}")

    # The slow part (running spaCy) happens before the database is touched.
    # Fillers, repetitions and caption markers are removed first; they are not
    # vocabulary and they mislead the parser.
    candidates = extract.extract_candidates(pipeline.parse(cleaning.clean(source.text)))
    groups = _group_by_item(candidates)

    counts: dict[str, int] = {}

    # One transaction: if anything fails, nothing of this import is saved.
    with conn:
        source_id = repo.add_source(
            conn, source.kind, source.ref, source.title, source.content_hash
        )
        for (kind, lemma), occurrences in groups.items():
            item = repo.find_item(conn, kind, lemma)
            is_new = item is None
            if item is None:
                item = _create_item(conn, kind, lemma, occurrences)

            for group in _groups_of(item, is_new, known_zipf):
                counts[group] = counts.get(group, 0) + 1

            for candidate in occurrences:
                repo.add_occurrence(
                    conn, item.id, source_id, candidate.sentence, candidate.surface_form
                )

    return ImportResult(source_id=source_id, **counts)


def _group_by_item(candidates: list[Candidate]) -> dict[tuple[ItemKind, str], list[Candidate]]:
    """Collect all occurrences of the same item, e.g. "runs" and "ran" under (word, "run")."""
    groups: dict[tuple[ItemKind, str], list[Candidate]] = {}
    for candidate in candidates:
        groups.setdefault((candidate.kind, candidate.lemma), []).append(candidate)
    return groups


def _create_item(
    conn: sqlite3.Connection, kind: ItemKind, lemma: str, occurrences: list[Candidate]
) -> Item:
    zipf = None
    if kind is ItemKind.WORD:  # phrases are not scored by frequency
        zipf = difficulty.zipf_score(lemma, forms=[c.surface_form for c in occurrences])

    item_id = repo.upsert_item(conn, kind, lemma, pos=occurrences[0].pos, zipf=zipf)
    return Item(
        id=item_id, kind=kind, lemma=lemma, pos=occurrences[0].pos, zipf=zipf, status=ItemStatus.NEW
    )


def _groups_of(item: Item, is_new: bool, known_zipf: float) -> list[str]:
    """The ImportResult counters this item belongs to."""
    if item.status in (ItemStatus.KNOWN, ItemStatus.IGNORED):
        return ["known_or_ignored"]
    if item.kind is ItemKind.WORD and difficulty.is_too_easy(item.zipf, known_zipf):
        return ["too_easy"]
    if not is_new:
        return ["seen_before"]
    if item.kind is ItemKind.PHRASAL_VERB:
        return ["new_phrasal_verbs"]
    if item.kind is ItemKind.IDIOM:
        return ["new_idioms"]
    return ["new_words", "unscored"] if item.zipf is None else ["new_words"]
