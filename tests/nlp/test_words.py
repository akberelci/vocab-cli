"""Word extraction on real English sentences.

These tests run the real spaCy model, so they also document what the model
gets right and where it has limits.
"""

from vocab.models import ItemKind
from vocab.nlp import pipeline, words


def extract(text):
    return list(words.extract_words(pipeline.parse(text)))


def lemmas(text):
    return [candidate.lemma for candidate in extract(text)]


# --- lemmatization -----------------------------------------------------------


def test_inflected_forms_are_reduced_to_their_base_form():
    assert lemmas("The children were running quickly through the darkest woods.") == [
        "the",
        "child",
        "be",
        "run",
        "quickly",
        "through",
        "the",
        "dark",
        "wood",
    ]


def test_irregular_verbs_are_reduced_to_their_base_form():
    assert lemmas("She bought a book, wrote notes and went home.") == [
        "she",
        "buy",
        "a",
        "book",
        "write",
        "note",
        "and",
        "go",
        "home",
    ]


def test_lemmas_are_lower_case_even_at_the_start_of_a_sentence():
    assert lemmas("Reluctant students rarely ask.")[0] == "reluctant"


def test_candidate_keeps_the_original_form_and_sentence():
    (candidate,) = [c for c in extract("The children were running.") if c.lemma == "child"]

    assert candidate.kind is ItemKind.WORD
    assert candidate.pos == "NOUN"
    assert candidate.surface_form == "children"
    assert candidate.sentence == "The children were running."


# --- nouns that end in "s" but are not plurals --------------------------------------


def test_noun_ending_in_ics_keeps_its_s():
    # spaCy's lemma is "geopolitic", which is not a word.
    assert "geopolitics" in lemmas("The geopolitics of oil changed everything.")
    assert "geopolitic" not in lemmas("The geopolitics of oil changed everything.")


def test_other_nouns_whose_shortened_form_is_far_rarer_keep_their_s():
    found = lemmas("She studied mathematics and wrote about several species of birds.")

    assert "mathematics" in found
    assert "species" in found
    assert not {"mathematic", "specie"} & set(found)


def test_ordinary_plurals_are_still_reduced_to_the_singular():
    found = lemmas("The athletes left their shoes and keys near the houses.")

    assert {"athlete", "shoe", "key", "house"} <= set(found)
    assert not {"athletes", "shoes", "keys", "houses"} & set(found)


def test_rare_plural_of_a_rare_word_is_still_reduced():
    # Both forms are rare, so there is no reason to distrust the lemma.
    assert "organiser" in lemmas("The organisers called off the race.")


def test_verb_forms_ending_in_s_are_not_affected():
    assert lemmas("She runs and he watches.") == ["she", "run", "and", "he", "watch"]


def test_known_limitation_economics_becomes_economic():
    # "economic" is itself a common word, so the guard cannot tell that the
    # lemma is wrong. See docs/KNOWN_ISSUES.md.
    assert "economic" in lemmas("He studied economics at university.")


# --- contractions ------------------------------------------------------------


def test_negative_contraction_is_split_into_verb_and_not():
    assert lemmas("I don't know.") == ["i", "do", "not", "know"]


def test_irregular_negative_contractions_get_the_right_verb():
    # "can't" is tokenized as "ca" + "n't", "won't" as "wo" + "n't".
    assert lemmas("He can't swim and won't try.") == [
        "he",
        "can",
        "not",
        "swim",
        "and",
        "will",
        "not",
        "try",
    ]


def test_is_contraction_becomes_be():
    assert lemmas("She's leaving tomorrow.") == ["she", "be", "leave", "tomorrow"]


def test_have_and_will_contractions_become_have_and_will():
    assert lemmas("They've finished, so we'll start.") == [
        "they",
        "have",
        "finish",
        "so",
        "we",
        "will",
        "start",
    ]


def test_possessive_s_is_dropped():
    # The "'s" in "sister's" is a possessive marker, not the verb "is".
    assert lemmas("My sister's car is old.") == ["my", "sister", "car", "be", "old"]


def test_curly_apostrophes_are_read_like_plain_ones():
    # Books and web pages use the typographic apostrophe: don’t, it’s.
    assert lemmas("She didn’t know it’s late.") == ["she", "do", "not", "know", "it", "be", "late"]


def test_apostrophe_inside_a_word_is_kept():
    found = extract("She set an alarm for six o'clock.")

    assert [c.lemma for c in found][-2:] == ["six", "o'clock"]
    assert found[-1].surface_form == "o'clock"


def test_curly_apostrophe_inside_a_word_is_kept():
    assert "o'clock" in lemmas("We met at six o’clock.")


# --- things that are not vocabulary ------------------------------------------


def test_punctuation_is_skipped():
    assert lemmas("Wait... really?! Yes: (very) nice — indeed.") == [
        "wait",
        "really",
        "yes",
        "very",
        "nice",
        "indeed",
    ]


def test_digits_money_and_ordinals_are_skipped():
    assert lemmas("She bought 3 houses for $250,000 in 2019 at the 3rd auction.") == [
        "she",
        "buy",
        "house",
        "for",
        "in",
        "at",
        "the",
        "auction",
    ]


def test_ordinals_written_with_digits_are_skipped():
    assert lemmas("On the 14th day she finished a 10 kilometre race.") == [
        "on",
        "the",
        "day",
        "she",
        "finish",
        "a",
        "kilometre",
        "race",
    ]


def test_written_out_number_words_are_kept():
    assert lemmas("There were twenty-three authors and six editors.") == [
        "there",
        "be",
        "twenty",
        "three",
        "author",
        "and",
        "six",
        "editor",
    ]


def test_written_out_ordinals_are_kept():
    # "at first" would lose its main word if "first" were treated as a number.
    found = lemmas("At first, she nearly gave up after the third week.")

    assert "first" in found
    assert "third" in found


def test_urls_and_email_addresses_are_skipped():
    found = lemmas("Visit https://example.com or write to me@example.com today.")

    assert found == ["visit", "or", "write", "to", "today"]


# --- proper names ------------------------------------------------------------


def test_person_names_are_skipped():
    assert lemmas("Yesterday Michael Jordan met Dr. Smith.") == ["yesterday", "meet"]


def test_place_names_are_skipped():
    assert lemmas("Emma moved to Istanbul and later to Germany.") == [
        "move",
        "to",
        "and",
        "later",
        "to",
    ]


def test_possessive_of_a_name_leaves_nothing_behind():
    assert lemmas("It's John's car.") == ["it", "be", "car"]


def test_small_words_inside_an_organisation_name_are_skipped():
    # "the" and "of" belong to the name here, so they are not vocabulary.
    assert lemmas("He visited the Bank of England.") == ["he", "visit"]


def test_days_and_months_are_skipped():
    assert lemmas("On Monday we will bake bread in March.") == [
        "on",
        "we",
        "will",
        "bake",
        "bread",
        "in",
    ]


def test_nationalities_are_skipped():
    assert lemmas("The Turkish economy grew.") == ["the", "economy", "grow"]


def test_a_word_that_is_also_a_surname_is_kept_when_used_as_a_word():
    # "Baker" is a name, "bake" and "baker" are words.
    found = lemmas("Mr. Baker asked the baker to bake more bread.")

    assert "baker" in found
    assert found.count("baker") == 1
    assert "bake" in found


# --- sentences ---------------------------------------------------------------


def test_each_candidate_carries_its_own_sentence():
    found = extract("The dog barked. A cat ran away.")

    sentences = {c.lemma: c.sentence for c in found}

    assert sentences["dog"] == "The dog barked."
    assert sentences["cat"] == "A cat ran away."


def test_line_breaks_inside_a_sentence_are_removed_from_the_example():
    # Text files are often wrapped at a fixed width.
    found = extract("The old man walked slowly\nalong the   empty beach.")

    assert {c.sentence for c in found} == {"The old man walked slowly along the empty beach."}
