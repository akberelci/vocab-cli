"""Extracting single words from parsed text.

Each token is reduced to its lemma (base form), and tokens that are not
vocabulary are skipped: punctuation, numbers written with digits, proper names,
URLs and so on.

Nothing is filtered by difficulty here. Very common words like "the" are still
returned; removing what you already know is the job of the difficulty module.
"""

import re
from collections.abc import Collection, Iterator

from spacy.tokens import Doc, Token

from vocab import difficulty
from vocab.models import Candidate, ItemKind
from vocab.nlp.examples import excerpt

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


def extract_words(doc: Doc, skip: Collection[int] = ()) -> Iterator[Candidate]:
    """Yield one candidate for every token in the text that counts as a word.

    `skip` holds positions of tokens to leave out, because they already belong
    to a phrase ("gave" and "up" in "gave up").
    """
    for sentence in doc.sents:
        for token in sentence:
            if token.i not in skip and _is_word(token):
                yield Candidate(
                    kind=ItemKind.WORD,
                    lemma=lemma_of(token),
                    pos=token.pos_,
                    surface_form=token.text,
                    sentence=excerpt(sentence, [token.i]),
                )


# How much more common the written form must be than spaCy's lemma (in Zipf
# points, so 1.0 means ten times) before the lemma is distrusted.
_LEMMA_DISTRUST = 1.0


def lemma_of(token: Token) -> str:
    """The base form of a word, in lower case.

    Normally this is spaCy's lemma. One mistake of the small model is repaired:
    it removes the final "s" of nouns that are not plurals, turning
    "geopolitics" into "geopolitic" and "species" into "specie". If such a
    shortened form is unknown or far rarer than the written word, the written
    word is kept.
    """
    lemma = token.lemma_.lower()
    written = token.lower_

    if token.pos_ == "NOUN" and written == lemma + "s":
        lemma_score = difficulty.zipf_score(lemma) or 0.0
        written_score = difficulty.zipf_score(written) or 0.0
        if written_score - lemma_score >= _LEMMA_DISTRUST:
            return written

    return lemma


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
