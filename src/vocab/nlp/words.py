"""Extracting single words from parsed text.

Each token is reduced to its lemma (base form), and tokens that are not
vocabulary are skipped: punctuation, numbers written with digits, proper names,
URLs and so on.

Nothing is filtered by difficulty here. Very common words like "the" are still
returned; removing what you already know is the job of the difficulty module.
"""

import re
from collections.abc import Iterator

from spacy.tokens import Doc, Token

from vocab.models import Candidate, ItemKind
from vocab.nlp.pipeline import sentence_text

# Part-of-speech tags that are never vocabulary:
# proper nouns, punctuation, symbols, "other" (URLs, noise) and whitespace.
# Numbers are not in this list on purpose: "six" is tagged as a number too,
# and written-out number words are kept (see _is_word).
_SKIPPED_POS = {"PROPN", "PUNCT", "SYM", "X", "SPACE"}

# Named-entity types that mark a name: people, countries and cities, other
# locations, organisations, buildings, and nationalities ("Turkish").
# Catches names the tagger did not mark as PROPN, and the small words inside
# a name ("of" in "Bank of England").
_NAME_ENTITY_TYPES = {"PERSON", "GPE", "LOC", "ORG", "FAC", "NORP"}

# What a lemma must look like: letters, optionally joined by apostrophes.
# Matches "clock" and "o'clock"; rejects "'s" (starts with the apostrophe).
# "[^\W\d_]" means "any letter", including accented ones like the "é" in "café".
_WORD_PATTERN = re.compile(r"[^\W\d_]+('[^\W\d_]+)*")


def extract_words(doc: Doc) -> Iterator[Candidate]:
    """Yield one candidate for every token in the text that counts as a word."""
    for sentence in doc.sents:
        text = sentence_text(sentence)
        for token in sentence:
            if _is_word(token):
                yield Candidate(
                    kind=ItemKind.WORD,
                    lemma=token.lemma_.lower(),
                    pos=token.pos_,
                    surface_form=token.text,
                    sentence=text,
                )


def _is_word(token: Token) -> bool:
    if token.pos_ in _SKIPPED_POS:
        return False
    # Anything written with digits is skipped: "10", "250,000", "14th", "3rd".
    # Written-out numbers ("six", "first") are ordinary words and are kept;
    # the difficulty filter removes the easy ones later.
    if any(character.isdigit() for character in token.text):
        return False
    if token.ent_type_ in _NAME_ENTITY_TYPES:
        return False
    # Checking the lemma instead of the token text keeps contractions that stand
    # for a real word ("n't" -> "not", "'ll" -> "will") and drops the possessive
    # "'s", whose lemma stays "'s".
    return _WORD_PATTERN.fullmatch(token.lemma_) is not None
