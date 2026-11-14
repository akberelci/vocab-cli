"""Extracting single words from parsed text.

Each token is reduced to its lemma (base form), and tokens that are not
vocabulary are skipped: punctuation, numbers, proper names, URLs and so on.

Nothing is filtered by difficulty here. Very common words like "the" are still
returned; removing what you already know is the job of the difficulty module.
"""

from collections.abc import Iterator

from spacy.tokens import Doc, Token

from vocab.models import Candidate, ItemKind
from vocab.nlp.pipeline import sentence_text

# Part-of-speech tags that are never vocabulary:
# proper nouns, numbers, punctuation, symbols, "other" (URLs, noise) and whitespace.
_SKIPPED_POS = {"PROPN", "NUM", "PUNCT", "SYM", "X", "SPACE"}

# Named-entity types that mark a name: people, countries and cities, other
# locations, organisations, buildings, and nationalities ("Turkish").
# Catches names the tagger did not mark as PROPN, and the small words inside
# a name ("of" in "Bank of England").
_NAME_ENTITY_TYPES = {"PERSON", "GPE", "LOC", "ORG", "FAC", "NORP"}


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
    if token.like_num:  # "42", "3rd", and number words like "twenty"
        return False
    if token.ent_type_ in _NAME_ENTITY_TYPES:
        return False
    # The lemma must consist of letters only. Checking the lemma instead of the
    # token text keeps contractions that stand for a real word ("n't" -> "not",
    # "'ll" -> "will") and drops the possessive "'s", whose lemma stays "'s".
    return token.lemma_.isalpha()
