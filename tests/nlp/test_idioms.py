"""Idiom detection on real English sentences.

Tests marked xfail are known limitations: they describe what the tool should
ideally do, and currently does not.
"""

import pytest

from vocab.models import ItemKind
from vocab.nlp import phrases, pipeline


def idioms(text):
    """The idioms found in a text, as (list entry, form in the text) pairs."""
    matches = phrases.find_idioms(pipeline.parse(text))
    return [(m.candidate.lemma, m.candidate.surface_form) for m in matches]


def test_fixed_expression_from_the_running_club_story():
    text = "At first, she couldn't keep up with the others."

    assert idioms(text) == [("at first", "At first")]


def test_idiom_with_the_verb_in_the_past_tense():
    assert idioms("Someone spilled the beans about the party.") == [
        ("spill the beans", "spilled the beans")
    ]


def test_idiom_with_the_verb_in_the_ing_form():
    assert idioms("It was raining cats and dogs, so we called it a day.") == [
        ("rain cats and dogs", "raining cats and dogs"),
        ("call it a day", "called it a day"),
    ]


def test_idiom_with_an_irregular_verb_form():
    assert idioms("He got cold feet and missed the boat.") == [
        ("get cold feet", "got cold feet"),
        ("miss the boat", "missed the boat"),
    ]


def test_idiom_without_a_verb():
    assert idioms("We only see each other once in a blue moon.") == [
        ("once in a blue moon", "once in a blue moon")
    ]


def test_several_idioms_in_one_text():
    text = "The news came out of the blue. Of course, nobody believed it at first."

    assert idioms(text) == [
        ("out of the blue", "out of the blue"),
        ("of course", "Of course"),
        ("at first", "at first"),
    ]


def test_longer_idiom_wins_over_a_shorter_one_inside_it():
    # Both "sit on the fence" and "on the fence" are in the list.
    assert idioms("He sat on the fence during the whole debate.") == [
        ("sit on the fence", "sat on the fence")
    ]
    assert idioms("She is still on the fence about it.") == [("on the fence", "on the fence")]


def test_fixed_part_of_an_idiom_with_a_changing_object():
    assert idioms("Please keep an eye on him.") == [("keep an eye on", "keep an eye on")]


def test_words_in_a_different_order_or_with_a_gap_do_not_match():
    assert idioms("He kicked the old bucket across the yard.") == []


def test_idiom_does_not_continue_into_the_next_sentence():
    # "at" ends one sentence and "First" starts the next.
    assert idioms("What are you looking at? First tell me.") == []


def test_text_without_idioms():
    assert idioms("She looked up the word in a dictionary.") == []


def test_match_describes_the_idiom_and_the_tokens_it_uses():
    doc = pipeline.parse("He finally kicked the bucket.")

    (match,) = phrases.find_idioms(doc)

    assert match.candidate.kind is ItemKind.IDIOM
    assert match.candidate.pos is None
    assert match.candidate.sentence == "He finally kicked the bucket."
    assert [doc[i].text for i in sorted(match.token_indexes)] == ["kicked", "the", "bucket"]


# --- known limitations -----------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: idioms with a changing part cannot be listed yet. "
    "'pull someone's leg' appears as 'pulled my leg', 'pulling his leg', and so on.",
)
def test_idiom_with_a_changing_possessive():
    assert idioms("Don't worry, she was only pulling my leg.") == [
        ("pull someone's leg", "pulling my leg")
    ]


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: the words of an idiom must be neighbours. An extra word "
    "inside the idiom ('makes perfect sense') breaks the match.",
)
def test_idiom_with_an_inserted_word():
    assert idioms("It makes perfect sense.") == [("make sense", "makes perfect sense")]


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: the tool recognises the wording, not the meaning. "
    "A cow that literally kicks a bucket is reported as the idiom.",
)
def test_literal_use_of_idiom_wording_is_not_offered():
    assert idioms("The cow kicked the bucket and the milk ran across the floor.") == []


# --- the list file ---------------------------------------------------------------


def test_shipped_list_is_well_formed():
    entries = phrases.parse_phrase_list(phrases.read_data_file("idioms.txt"))

    assert len(entries) > 80
    assert len(entries) == len(set(entries)), "duplicate entries"
    for entry in entries:
        assert len(entry.split()) >= 2, entry


def test_listed_idioms_are_grouped_by_first_word():
    by_first_word = phrases.listed_idioms()

    assert ("kick", "the", "bucket") in by_first_word["kick"]
    assert ("at", "first") in by_first_word["at"]
