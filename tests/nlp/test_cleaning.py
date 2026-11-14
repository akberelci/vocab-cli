"""Text cleaning, on short sentences written to show each kind of noise found
in auto-generated captions."""

import pytest

from vocab.nlp import cleaning
from vocab.nlp.cleaning import clean

# --- markers ---------------------------------------------------------------------


def test_speaker_change_marker_is_removed():
    assert clean(">> I think that is right >> yes it is") == "I think that is right yes it is"


def test_sound_descriptions_in_brackets_are_removed():
    assert clean("[Music] welcome back [Applause] thank you") == "welcome back thank you"


def test_line_that_is_only_a_marker_does_not_leave_a_paragraph_break():
    assert clean("we were talking\n\n[Music]\n\nabout the weather") == (
        "we were talking\n\nabout the weather"
    )


def test_normal_brackets_in_prose_are_left_alone():
    assert clean("She smiled (a little) and left.") == "She smiled (a little) and left."


# --- fillers ---------------------------------------------------------------------


@pytest.mark.parametrize("filler", sorted(cleaning.FILLERS))
def test_each_filler_is_removed(filler):
    assert clean(f"the problem is {filler} quite serious") == "the problem is quite serious"


def test_filler_is_removed_together_with_its_comma():
    assert clean("Well, um, I think so.") == "Well, I think so."


def test_capital_letter_moves_to_the_next_word_when_a_sentence_starts_with_a_filler():
    assert clean("Uh, the answer is no.") == "The answer is no."


def test_full_stop_after_a_filler_at_the_end_of_a_sentence_is_kept():
    assert clean("It is quite serious, um. Nobody knows why.") == (
        "It is quite serious. Nobody knows why."
    )


def test_fillers_are_whole_words_only():
    # "summer" contains "um", "her" contains "er", "erm" is inside "term".
    text = "Her summer term was long."

    assert clean(text) == text


def test_abbreviation_in_capitals_is_not_a_filler():
    assert clean("He was taken to the ER at night.") == "He was taken to the ER at night."


def test_real_words_often_used_as_fillers_are_kept():
    text = "It was, like, you know, a surprise."

    assert clean(text) == text


# --- repetitions -----------------------------------------------------------------


def test_repeated_word_is_collapsed():
    assert clean("she lives in in Brazil") == "she lives in Brazil"


def test_word_repeated_several_times_is_collapsed_to_one():
    assert clean("and and and I think so") == "and I think so"


def test_repetition_hidden_behind_a_filler_is_collapsed():
    assert clean("what is happening in in um in Brazil") == "what is happening in Brazil"


def test_repeated_contraction_is_collapsed():
    assert clean("it's it's really hard") == "it's really hard"


def test_repeated_pair_of_words_is_collapsed():
    assert clean("I think I think we should go") == "I think we should go"


def test_several_kinds_of_repetition_in_one_sentence():
    assert clean("I mean I mean it's it's hard to to keep up with with everything") == (
        "I mean it's hard to keep up with everything"
    )


def test_repetition_ignores_capital_letters_and_keeps_the_capital():
    assert clean("The the problem is clear.") == "The problem is clear."


def test_repetition_across_a_line_break_is_collapsed():
    # Captions break lines at arbitrary places.
    assert clean("what is happening in\nin Brazil") == "what is happening in Brazil"


def test_repetition_with_punctuation_in_between_is_deliberate():
    text = "It was very, very good. No. No, thank you."

    assert clean(text) == text


def test_repeated_numbers_are_not_collapsed():
    assert clean("the score was 20 20 at half time") == "the score was 20 20 at half time"


@pytest.mark.parametrize(
    "text",
    [
        "He had had enough of it.",
        "I know that that is true.",
        "She waved and said bye bye.",
        "The film was only so so.",
        "No no, that is not what I meant.",
        "It was a very very long day.",
    ],
)
def test_doubled_words_that_are_normal_english_are_kept(text):
    assert clean(text) == text


def test_exceptions_are_listed_in_lower_case():
    assert all(word == word.lower() for word in cleaning.ALLOWED_REPEATS)
    assert {"had", "that", "bye", "so", "no"} <= cleaning.ALLOWED_REPEATS


# --- text structure ---------------------------------------------------------------


def test_clean_text_is_not_changed():
    text = "She gave up smoking last year. It was not easy."

    assert clean(text) == text


def test_paragraph_breaks_are_kept_and_line_breaks_become_spaces():
    text = "The first line\ncontinues here.\n\nA new paragraph."

    assert clean(text) == "The first line continues here.\n\nA new paragraph."


def test_empty_text_stays_empty():
    assert clean("") == ""
    assert clean("  \n\n  ") == ""


def test_everything_together():
    text = ">> so what is happening in in um in Brazil right now is uh very serious"

    assert clean(text) == "so what is happening in Brazil right now is very serious"
