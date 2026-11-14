"""Example sentences: cutting very long ones down, and choosing the best one.

Text without punctuation (auto-generated captions) gives "sentences" that run
on for hundreds of words. Two things keep examples readable:

1. excerpt() is used when a text is imported. A sentence of up to MAX_WORDS
   words is stored whole; a longer one is cut to a window around the target.
2. best_example() is used when an item is shown. Among all the sentences an
   item was seen in, it picks the one that makes the best example.
"""

from collections.abc import Collection, Sequence

from spacy.tokens import Span, Token

from vocab.models import Occurrence
from vocab.nlp.pipeline import sentence_text

MAX_WORDS = 25  # longer sentences are cut
CONTEXT_WORDS = 10  # words kept on each side of the target when cutting
CUT_MARK = "..."

# A good example is long enough to give context and short enough to read at a glance.
IDEAL_WORDS = range(6, 21)  # 6 to 20 words


def _is_word(token: Token) -> bool:
    return not (token.is_punct or token.is_space)


# --- cutting long sentences ------------------------------------------------------


def excerpt(sentence: Span, target: Collection[int]) -> str:
    """The sentence as example text for the tokens at the `target` positions.

    A separated phrase ("turned ... off") is always kept complete: the window
    starts before its first token and ends after its last one.
    """
    if sum(_is_word(token) for token in sentence) <= MAX_WORDS:
        return sentence_text(sentence)

    doc = sentence.doc
    start = _walk(doc, min(target), sentence.start, step=-1)
    end = _walk(doc, max(target), sentence.end - 1, step=+1)

    text = sentence_text(doc[start : end + 1])
    if start > sentence.start:
        text = f"{CUT_MARK} {text}"
    if end < sentence.end - 1:
        text = f"{text} {CUT_MARK}"
    return text


def _walk(doc, position: int, limit: int, step: int) -> int:
    """Move from `position` towards `limit` until CONTEXT_WORDS words were passed.

    Returns the position of the last word reached, so the excerpt never starts
    or ends with a loose punctuation mark.
    """
    reached = position
    words = 0
    while position != limit and words < CONTEXT_WORDS:
        position += step
        if _is_word(doc[position]):
            words += 1
            reached = position
    return reached


# --- choosing the best example -----------------------------------------------------


def is_cut(sentence: str) -> bool:
    return sentence.startswith(f"{CUT_MARK} ") or sentence.endswith(f" {CUT_MARK}")


def best_example(occurrences: Sequence[Occurrence]) -> Occurrence | None:
    """The occurrence whose sentence makes the best example, or None if there are none.

    Ranking, most important first:
      1. a complete sentence beats a cut one;
      2. a length inside IDEAL_WORDS beats one outside, and outside the range
         the one closest to it wins;
      3. the shorter sentence wins;
      4. the one seen first wins.
    """
    if not occurrences:
        return None

    def rank(numbered: tuple[int, Occurrence]) -> tuple[bool, int, int, int]:
        order, occurrence = numbered
        length = len(occurrence.sentence.split())
        return (is_cut(occurrence.sentence), _distance_from_ideal(length), length, order)

    # min() compares the rank tuples from left to right, which gives exactly
    # the "most important first" order above.
    return min(enumerate(occurrences), key=rank)[1]


def _distance_from_ideal(length: int) -> int:
    if length < IDEAL_WORDS.start:
        return IDEAL_WORDS.start - length
    if length >= IDEAL_WORDS.stop:
        return length - (IDEAL_WORDS.stop - 1)
    return 0
