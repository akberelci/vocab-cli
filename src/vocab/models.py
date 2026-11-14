"""Plain data types shared between modules.

These carry data only. They do not know about the database, spaCy or the CLI,
so every module can import them without creating circular dependencies.
"""

from dataclasses import dataclass
from enum import StrEnum

# StrEnum members behave like normal strings ("word", "known", ...), so they can
# be stored in SQLite directly, while a typo like ItemKind.WROD fails immediately.
# The allowed values must match the CHECK constraints in storage/schema.sql.


class SourceKind(StrEnum):
    FILE = "file"
    YOUTUBE = "youtube"


class ItemKind(StrEnum):
    WORD = "word"
    PHRASAL_VERB = "phrasal_verb"
    IDIOM = "idiom"


class ItemStatus(StrEnum):
    NEW = "new"  # extracted, not yet decided
    KNOWN = "known"  # you already know it
    IGNORED = "ignored"  # not worth learning (names, noise)
    LEARNING = "learning"  # has a card and is being reviewed


@dataclass(frozen=True)
class Item:
    id: int
    kind: ItemKind
    lemma: str
    pos: str | None
    zipf: float | None
    status: ItemStatus


@dataclass(frozen=True)
class Occurrence:
    sentence: str
    surface_form: str
