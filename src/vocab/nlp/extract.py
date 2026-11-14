"""Everything worth learning in a text: phrases first, then the remaining words."""

from spacy.tokens import Doc

from vocab.models import Candidate
from vocab.nlp import phrases, words


def extract_candidates(doc: Doc) -> list[Candidate]:
    phrasal_verbs = phrases.find_phrasal_verbs(doc)

    # The tokens of a phrasal verb are not offered again as single words.
    # This is per token, not per word: in "She gave up, so he gave her a book"
    # only the first "gave" is part of "give up"; the second one is still a word.
    used: set[int] = set()
    for match in phrasal_verbs:
        used |= match.token_indexes

    return [
        *(match.candidate for match in phrasal_verbs),
        *words.extract_words(doc, skip=used),
    ]
