"""Cutting long sentences and choosing the best example.

The long "sentences" imitate auto-generated captions: no punctuation at all.
"""

from vocab.models import ItemKind, Occurrence
from vocab.nlp import examples, extract, pipeline
from vocab.nlp.examples import best_example

# 40 words without punctuation, with "reluctant" in the middle (word 20).
LONG = (
    "so we went to the old market near the river early in the morning and "
    "the owner was reluctant to talk about the prices because he thought "
    "that we were from the local newspaper and wanted a story"
)


def sentence_of(text, lemma, kind=ItemKind.WORD):
    """The stored example sentence for one item of a text."""
    candidates = extract.extract_candidates(pipeline.parse(text))
    (found,) = [c.sentence for c in candidates if c.lemma == lemma and c.kind is kind]
    return found


def occurrences(*sentences):
    return [Occurrence(sentence=sentence, surface_form="x") for sentence in sentences]


# --- cutting -----------------------------------------------------------------------


def test_short_sentence_is_stored_whole():
    text = "The owner was reluctant to talk about the prices."

    assert sentence_of(text, "reluctant") == text


def test_sentence_of_exactly_the_maximum_length_is_stored_whole():
    text = " ".join(["word"] * 24 + ["reluctant"]) + "."

    assert len(text.split()) == examples.MAX_WORDS
    assert sentence_of(text, "reluctant") == text


def test_long_sentence_is_cut_to_ten_words_on_each_side():
    assert sentence_of(LONG, "reluctant") == (
        "... the river early in the morning and the owner was reluctant "
        "to talk about the prices because he thought that we ..."
    )


def test_cut_at_the_start_of_a_sentence_has_no_leading_mark():
    assert sentence_of(LONG, "market") == (
        "so we went to the old market near the river early in the morning and the owner ..."
    )


def test_cut_at_the_end_of_a_sentence_has_no_trailing_mark():
    assert sentence_of(LONG, "story") == (
        "... that we were from the local newspaper and wanted a story"
    )


def test_each_word_of_a_long_sentence_gets_its_own_window():
    assert sentence_of(LONG, "market") != sentence_of(LONG, "reluctant")


def test_window_counts_words_not_punctuation():
    text = (
        "Well, yes, no, maybe, perhaps, anyway, the owner, sadly, was reluctant, we heard, "
        "to talk about the prices, the weather, the river, the market, the newspaper, "
        "the story, and so on."
    )

    cut = sentence_of(text, "reluctant")

    before, after = cut.split("reluctant")
    assert len(before.replace("...", "").replace(",", "").split()) == examples.CONTEXT_WORDS
    assert len(after.replace("...", "").replace(",", "").split()) == examples.CONTEXT_WORDS
    assert not cut.startswith("... ,")


def test_separated_phrasal_verb_is_kept_complete_in_the_window():
    text = (
        "so every single evening before she went up to bed she turned the "
        "very old and noisy radio in the kitchen off and then she checked "
        "the door and the windows and the lights in the hall"
    )

    cut = sentence_of(text, "turn off", ItemKind.PHRASAL_VERB)

    assert "turned the very old and noisy radio in the kitchen off" in cut
    assert cut.startswith("... ") and cut.endswith(" ...")
    before, after = cut.split("turned the very old and noisy radio in the kitchen off")
    assert len(before.replace("...", "").split()) == examples.CONTEXT_WORDS
    assert len(after.replace("...", "").split()) == examples.CONTEXT_WORDS


def test_idiom_in_a_long_sentence_is_kept_complete():
    text = LONG.replace("was reluctant to talk", "finally decided to call it a day and talk")

    cut = sentence_of(text, "call it a day", ItemKind.IDIOM)

    assert "call it a day" in cut
    assert examples.is_cut(cut)


# --- recognising a cut sentence ---------------------------------------------------------


def test_cut_sentences_are_recognised_by_their_marks():
    assert examples.is_cut("... the owner was reluctant to talk ...")
    assert examples.is_cut("... wanted a story")
    assert examples.is_cut("so we went to the market ...")


def test_ordinary_ellipsis_in_prose_is_not_a_cut():
    assert not examples.is_cut("She waited... and waited.")
    assert not examples.is_cut("Well...")


# --- choosing the best example ------------------------------------------------------------


def test_no_occurrences_means_no_example():
    assert best_example([]) is None


def test_single_occurrence_is_the_best_one():
    (only,) = occurrences("She gave up.")

    assert best_example([only]) is only


def test_complete_sentence_beats_a_cut_one():
    found = occurrences(
        "... the owner was reluctant to talk about the prices because ...",
        "The reluctant owner of the old market near the river finally agreed to talk to us "
        "about his prices that morning.",
    )

    assert best_example(found) is found[1]  # complete, although longer


def test_sentence_of_ideal_length_beats_a_fragment():
    found = occurrences(
        "She gave up.",
        "After three weeks of training, she nearly gave up.",
    )

    # "Shortest" would pick the fragment, which shows almost no context.
    assert best_example(found) is found[1]


def test_sentence_of_ideal_length_beats_a_very_long_one():
    found = occurrences(
        "After three weeks of hard training in the cold and the rain with a group she hardly "
        "knew, she nearly gave up and went home.",
        "After three weeks of training, she nearly gave up.",
    )

    assert best_example(found) is found[1]


def test_among_ideal_sentences_the_shorter_one_wins():
    found = occurrences(
        "After three weeks of training in the cold, she nearly gave up.",
        "After three weeks of training, she nearly gave up.",
    )

    assert best_example(found) is found[1]


def test_outside_the_ideal_range_the_closest_length_wins():
    found = occurrences(
        "She gave up.",  # 3 words: three short of six
        " ".join(["word"] * 22) + ".",  # 22 words: two over twenty
    )

    assert best_example(found) is found[1]


def test_equal_sentences_keep_the_first_one_seen():
    found = occurrences(
        "After three weeks, she nearly gave up.",
        "After seven weeks, he nearly gave up.",
    )

    assert best_example(found) is found[0]


def test_among_cut_sentences_the_same_rules_apply():
    found = occurrences(
        "... and the owner was reluctant to talk about the prices because he thought that we ...",
        "... the owner was reluctant to talk ...",
    )

    assert best_example(found) is found[1]
