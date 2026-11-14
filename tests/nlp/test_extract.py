"""Phrases and words together: what a text finally yields."""

from vocab.models import ItemKind
from vocab.nlp import extract, pipeline


def extract_all(text):
    return extract.extract_candidates(pipeline.parse(text))


def lemmas(candidates, kind):
    return [c.lemma for c in candidates if c.kind is kind]


def test_phrasal_verb_replaces_its_verb_and_particle():
    found = extract_all("She gave up smoking.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["give up"]
    assert lemmas(found, ItemKind.WORD) == ["she", "smoking"]


def test_separated_phrasal_verb_keeps_the_words_in_between():
    found = extract_all("Turn the light off.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["turn off"]
    assert lemmas(found, ItemKind.WORD) == ["the", "light"]


def test_three_part_phrasal_verb_replaces_all_three_words():
    found = extract_all("Everyone put up with the cold weather.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["put up with"]
    assert lemmas(found, ItemKind.WORD) == ["everyone", "the", "cold", "weather"]


def test_only_the_tokens_inside_the_phrase_are_suppressed_not_the_word_everywhere():
    # "put", "up" and "with" each appear twice: once inside "put up with",
    # and once on their own in the second sentence.
    text = (
        "Everyone put up with the cold weather. "
        "Later she put her keys in her bag and walked up the stairs with a friend."
    )

    found = extract_all(text)

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["put up with"]
    own_words = [c for c in found if c.kind is ItemKind.WORD and c.lemma in ("put", "up", "with")]
    assert [c.lemma for c in own_words] == ["put", "up", "with"]
    assert {c.sentence for c in own_words} == {
        "Later she put her keys in her bag and walked up the stairs with a friend."
    }


def test_same_verb_inside_and_outside_a_phrase_in_one_sentence():
    found = extract_all("She gave up, so he gave her a book.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["give up"]
    assert lemmas(found, ItemKind.WORD).count("give") == 1
    assert "up" not in lemmas(found, ItemKind.WORD)


def test_literal_preposition_stays_a_word():
    found = extract_all("He ran up the hill.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == []
    assert lemmas(found, ItemKind.WORD) == ["he", "run", "up", "the", "hill"]


def test_idiom_is_offered_together_with_its_single_words():
    found = extract_all("Someone spilled the beans.")

    assert lemmas(found, ItemKind.IDIOM) == ["spill the beans"]
    assert lemmas(found, ItemKind.WORD) == ["someone", "spill", "the", "bean"]


def test_phrasal_verb_and_idiom_in_one_sentence():
    found = extract_all("At first, she nearly gave up.")

    assert lemmas(found, ItemKind.PHRASAL_VERB) == ["give up"]
    assert lemmas(found, ItemKind.IDIOM) == ["at first"]
    assert lemmas(found, ItemKind.WORD) == ["at", "first", "she", "nearly"]
