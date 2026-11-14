"""How difficult a word is, estimated from how often it is used.

The measure is the Zipf scale from the `wordfreq` library:

    7  about once every hundred words      ("the")
    5  100 times per million words         ("decision")
    4  10 times per million words          ("athlete")
    3  once per million words              ("obfuscate" is lower still)

Each step down is ten times rarer. Rare words are assumed to be harder.

Only single words are scored. A phrasal verb like "give up" consists of very
common words but is still worth learning, so phrases have no score.
"""

from collections.abc import Iterable

from wordfreq import zipf_frequency


def zipf_score(lemma: str, forms: Iterable[str] = ()) -> float | None:
    """The Zipf score of a word: the highest score among its lemma and the
    forms it was written in. Returns None if wordfreq knows none of them.

    Why the highest? Sometimes the base form is rarer than a form everybody
    knows ("disappoint" 3.67, "disappointed" 4.42), and sometimes spaCy picks a
    strange base form ("data" becomes "datum"). If any form of the word is
    common, the word is not new to the reader.
    """
    spellings = {lemma.lower(), *(form.lower() for form in forms)}
    best = max(zipf_frequency(spelling, "en") for spelling in spellings)

    # wordfreq answers 0 for anything it has never seen: very rare words,
    # typos, foreign words. That is "unknown", not "extremely rare".
    return round(best, 2) if best > 0 else None


def is_too_easy(zipf: float | None, known_zipf: float) -> bool:
    """Is a word common enough to count as known at this threshold?

    Words without a score are never "too easy": we cannot tell, so they stay
    visible and the user decides.
    """
    return zipf is not None and zipf >= known_zipf
