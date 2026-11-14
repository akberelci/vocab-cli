"""Cleaning text before it is parsed.

Spoken language written down (auto-generated captions, interview transcripts)
contains things that are not vocabulary and that confuse the parser:

    markers       >>   [Music]   [Applause]
    fillers       uh, um, er
    repetitions   "and and and", "in in", "it's it's", "I think I think"

clean() removes them. The cleaned text is what gets parsed and what example
sentences are taken from; the original text is not kept.
"""

import re

# Sounds people make while thinking. Compared in lower case, as whole words.
FILLERS = frozenset({"uh", "um", "uhm", "er", "erm", "hmm"})

# Words that are normal English when doubled, so the repetition is kept:
# "he had had enough", "I know that that is true", "bye bye", "so so", "no no".
# To add an exception, add the word here in lower case.
ALLOWED_REPEATS = frozenset(
    {"had", "that", "bye", "so", "no", "very", "really", "ha", "there", "now", "knock", "blah"}
)

# ">>" marks a change of speaker in captions; "[Music]" describes a sound.
_MARKERS = re.compile(r">{2,}|\[[^\]\n]{1,40}\]")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = ".?!"


def clean(text: str) -> str:
    """Remove markers, fillers and immediate repetitions from a text.

    Blank lines (paragraph breaks) are kept; single line breaks become spaces.
    """
    paragraphs = (_clean_paragraph(paragraph) for paragraph in _PARAGRAPH_BREAK.split(text))
    # A paragraph that consisted only of "[Music]" is dropped completely.
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _clean_paragraph(paragraph: str) -> str:
    words = _MARKERS.sub(" ", paragraph).split()
    words = _remove_fillers(words)

    # Removing one repetition can reveal another ("in in um in" -> "in in" -> "in"),
    # so repeat until nothing changes.
    while True:
        shorter = _collapse_repeats(_collapse_repeats(words, size=1), size=2)
        if len(shorter) == len(words):
            break
        words = shorter

    return " ".join(words)


def _core(word: str) -> str:
    """The word without surrounding punctuation, in lower case: '"Um,' -> 'um'."""
    return word.strip(".,;:!?\"'()-").lower()


def _starts_upper(word: str) -> bool:
    return word[:1].isupper()


def _capitalise(word: str) -> str:
    return word[:1].upper() + word[1:]


def _remove_fillers(words: list[str]) -> list[str]:
    kept: list[str] = []
    capitalise_next = False

    for word in words:
        # An all-capitals "ER" is an abbreviation (emergency room), not a filler.
        is_filler = _core(word) in FILLERS and not (word.isupper() and len(word) > 1)

        if is_filler:
            # "..., um." ends a sentence: keep the full stop on the word before.
            if word[-1] in _SENTENCE_END and kept and kept[-1][-1] not in _SENTENCE_END:
                kept[-1] = kept[-1].rstrip(",;:") + word[-1]
            # "Um, the problem" -> "The problem"
            capitalise_next = capitalise_next or _starts_upper(word)
            continue

        kept.append(_capitalise(word) if capitalise_next else word)
        capitalise_next = False

    return kept


def _collapse_repeats(words: list[str], size: int) -> list[str]:
    """Drop a group of `size` words when the same group follows it directly.

    size=1: "and and and I" -> "and I"        size=2: "it is it is hard" -> "it is hard"
    """
    kept: list[str] = []
    position = 0

    while position < len(words):
        group = words[position : position + size]
        following = words[position + size : position + 2 * size]

        if _is_repeat(group, following):
            # Skip this group and keep the next one, but keep a capital letter:
            # "The the problem" -> "The problem".
            if _starts_upper(group[0]) and not _starts_upper(following[0]):
                words = [*words]
                words[position + size] = _capitalise(following[0])
            position += size
        else:
            kept.append(words[position])
            position += 1

    return kept


def _is_repeat(group: list[str], following: list[str]) -> bool:
    if len(following) < len(group):
        return False
    if [_core(word) for word in group] != [_core(word) for word in following]:
        return False
    # Only real words: "- -" or "10 10" are not disfluencies.
    if not all(_core(word).replace("'", "").isalpha() for word in group):
        return False
    # Punctuation in between means the repetition is deliberate: "very, very good",
    # "No. No!".
    if any(word[-1] in ".,;:!?" for word in group):
        return False
    return not (len(group) == 1 and _core(group[0]) in ALLOWED_REPEATS)
