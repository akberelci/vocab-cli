"""Loading the spaCy model and running it on text.

This is the only place that loads the model, so the rest of the code does not
care which model is used or how it is configured.
"""

from functools import lru_cache

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span

MODEL_NAME = "en_core_web_sm"


class ModelNotInstalledError(Exception):
    """The spaCy English model is missing from the environment."""


# Loading the model takes about a second, so it is done once and then reused:
# lru_cache remembers the result of the first call.
@lru_cache(maxsize=1)
def get_nlp() -> Language:
    try:
        return spacy.load(MODEL_NAME)
    except OSError:
        raise ModelNotInstalledError(
            f"The spaCy model '{MODEL_NAME}' is not installed. "
            "Run `uv sync` in the project folder to install it."
        ) from None


def parse(text: str) -> Doc:
    """Run the full spaCy pipeline: tokens, lemmas, part-of-speech tags,
    the dependency parse (also used for sentence boundaries) and named entities."""
    return get_nlp()(text)


def sentence_text(sentence: Span) -> str:
    """The sentence as one clean line: line breaks and repeated spaces become one space."""
    return " ".join(sentence.text.split())
