"""Loading the spaCy model and running it on text.

This is the only place that loads the model, so the rest of the code does not
care which model is used or how it is configured.
"""

from functools import lru_cache

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span

MODEL_NAME = "en_core_web_sm"

_QUOTE_MARKS = {'"', "'", "“", "”", "«", "»"}


class ModelNotInstalledError(Exception):
    """The spaCy English model is missing from the environment."""


# spaCy decides sentence boundaries while parsing, and it gets two things wrong
# in ordinary prose. This small step runs just before the parser and fixes the
# boundaries the parser is not allowed to change afterwards:
#   token.is_sent_start = False  -> "a sentence must not start here"
#   token.is_sent_start = True   -> "a sentence must start here"
@Language.component("vocab_sentence_boundaries")
def _fix_sentence_boundaries(doc: Doc) -> Doc:
    for token in doc[1:]:
        previous = doc[token.i - 1]

        if _is_paragraph_break(token):
            # The blank line itself stays at the end of the paragraph before it.
            token.is_sent_start = False
        elif _is_paragraph_break(previous):
            # A blank line always ends a sentence, even without a full stop
            # (headings, list items).
            token.is_sent_start = True
        elif token.text in _QUOTE_MARKS and not previous.is_space and not previous.whitespace_:
            # A quote mark glued to the text before it (`improvements."`) is a
            # closing quote, so it belongs to the sentence it closes. Without
            # this rule, a closing quote at the end of a paragraph becomes the
            # first character of the next sentence.
            token.is_sent_start = False

    return doc


def _is_paragraph_break(token) -> bool:
    return token.is_space and token.text.count("\n") >= 2


# Loading the model takes about a second, so it is done once and then reused:
# lru_cache remembers the result of the first call.
@lru_cache(maxsize=1)
def get_nlp() -> Language:
    try:
        nlp = spacy.load(MODEL_NAME)
    except OSError:
        raise ModelNotInstalledError(
            f"The spaCy model '{MODEL_NAME}' is not installed. "
            "Run `uv sync` in the project folder to install it."
        ) from None

    nlp.add_pipe("vocab_sentence_boundaries", before="parser")
    return nlp


def parse(text: str) -> Doc:
    """Run the full spaCy pipeline: tokens, lemmas, part-of-speech tags,
    the dependency parse (also used for sentence boundaries) and named entities."""
    return get_nlp()(_normalise(text))


def _normalise(text: str) -> str:
    """Replace typographic apostrophes (’ and ‘) with the plain one (').

    Books and web pages write "don’t" with a curly apostrophe. The small model
    was mostly trained on the plain one and mis-reads the curly form: it turns
    the "n’t" of "didn’t" into a noun instead of "not".
    """
    return text.replace("’", "'").replace("‘", "'")


def sentence_text(sentence: Span) -> str:
    """The sentence as one clean line: line breaks and repeated spaces become one space."""
    return " ".join(sentence.text.split())
