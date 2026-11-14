"""Finding multi-word expressions: phrasal verbs (and, in the next step, idioms).

A phrasal verb is found in two ways, and the longer result wins:

1. Particle rule. spaCy's parser marks a word as the "particle" of a verb
   (dependency label "prt"): "gave up", "turned the light off".
2. List rule. The verb is looked up in data/phrasal_verbs.txt, and the words
   after it are compared with the listed phrasal verbs for that verb:
   "look forward to", "put up with", "run into".
"""

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

from spacy.tokens import Doc, Token

from vocab.models import Candidate, ItemKind
from vocab.nlp.pipeline import sentence_text


@dataclass(frozen=True)
class PhraseMatch:
    candidate: Candidate
    # Positions (in the document) of the tokens that form the phrase. Word
    # extraction uses them to avoid offering "give" and "up" next to "give up".
    token_indexes: frozenset[int]


# --- reading the list files ---------------------------------------------------


def parse_phrase_list(text: str) -> list[str]:
    """Turn the content of a list file into clean phrases.

    Comments (# ...) and empty lines are dropped, case and extra spaces are ignored.
    """
    phrases = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        phrase = " ".join(line.lower().split())
        if phrase:
            phrases.append(phrase)
    return phrases


def read_data_file(name: str) -> str:
    return resources.files("vocab.nlp").joinpath("data", name).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def listed_phrasal_verbs() -> dict[str, list[tuple[str, ...]]]:
    """The phrasal verb list, grouped by verb.

    {"look": [("after",), ("forward", "to"), ...], "put": [("up", "with"), ...]}
    """
    by_verb: dict[str, list[tuple[str, ...]]] = {}
    for phrase in parse_phrase_list(read_data_file("phrasal_verbs.txt")):
        verb, *parts = phrase.split()
        if parts:
            by_verb.setdefault(verb, []).append(tuple(parts))
    return by_verb


# --- phrasal verbs ------------------------------------------------------------


def find_phrasal_verbs(doc: Doc) -> list[PhraseMatch]:
    matches = []
    for token in doc:
        if token.pos_ != "VERB":
            continue
        parts = _phrasal_verb_parts(token)
        if parts:
            matches.append(_phrasal_verb_match(token, parts))
    return matches


def _phrasal_verb_parts(verb: Token) -> list[Token] | None:
    """The tokens that complete a phrasal verb ("up", or "up" + "with"), if any."""
    options = []

    particle = _particle_of(verb)
    if particle is not None:
        options.append([particle])

    for listed_parts in listed_phrasal_verbs().get(verb.lemma_.lower(), []):
        found = _match_listed_parts(verb, listed_parts)
        if found is not None:
            options.append(found)

    # Longest match wins: "put up with" (2 parts) beats "put up" (1 part).
    # max() keeps the first of equally long options, so the parser's particle
    # is preferred when both rules find a two-word verb.
    return max(options, key=len, default=None)


def _particle_of(verb: Token) -> Token | None:
    """Rule 1: the word spaCy's parser marked as this verb's particle."""
    for child in verb.children:
        if child.dep_ == "prt" and child.i > verb.i and child.text.isalpha():
            return child
    return None


def _match_listed_parts(verb: Token, listed_parts: tuple[str, ...]) -> list[Token] | None:
    """Rule 2: check one listed phrasal verb against the words after the verb.

    For "look forward to", listed_parts is ("forward", "to").
    """
    first_word, *later_words = listed_parts

    first = _find_first_part(verb, first_word)
    if first is None:
        return None

    # Every later part must come directly after the part before it:
    # "put up with" matches, "put the tent up with a friend" still does (a known
    # limit), but "put up a tent with a friend" does not.
    found = [first]
    for word in later_words:
        following = _next_in_sentence(found[-1])
        if following is None or following.lower_ != word:
            return None
        found.append(following)
    return found


def _find_first_part(verb: Token, word: str) -> Token | None:
    # Usual case: the word comes directly after the verb ("looks after", "ran into").
    following = _next_in_sentence(verb)
    if following is not None and following.lower_ == word:
        return following

    # Separated case: the object stands in between ("threw it away",
    # "turned the light off"). To avoid picking up an unrelated word further
    # along, it must be attached to this verb as a particle or an adverb.
    for child in verb.children:
        if child.i > verb.i and child.dep_ in ("prt", "advmod") and child.lower_ == word:
            return child
    return None


def _next_in_sentence(token: Token) -> Token | None:
    position = token.i + 1
    if position < token.sent.end:
        return token.doc[position]
    return None


def _phrasal_verb_match(verb: Token, parts: list[Token]) -> PhraseMatch:
    tokens = [verb, *parts]
    lemma = " ".join([verb.lemma_.lower(), *(part.lower_ for part in parts)])
    candidate = Candidate(
        kind=ItemKind.PHRASAL_VERB,
        lemma=lemma,
        pos="VERB",
        surface_form=_surface_form(tokens),
        sentence=sentence_text(verb.sent),
    )
    return PhraseMatch(candidate=candidate, token_indexes=frozenset(t.i for t in tokens))


def _surface_form(tokens: list[Token]) -> str:
    """The phrase as written, with "..." where other words stand in between:
    "gave up", "turned ... off"."""
    text = tokens[0].text
    for previous, token in zip(tokens, tokens[1:], strict=False):
        separator = " " if token.i == previous.i + 1 else " ... "
        text += separator + token.text
    return text
