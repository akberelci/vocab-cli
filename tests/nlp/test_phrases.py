"""Phrasal verb detection on real English sentences.

Most sentences come from the running-club story used as the project's test
text. Tests marked xfail are known limitations: they describe what the tool
should ideally do, and currently does not.
"""

import pytest

from vocab.models import ItemKind
from vocab.nlp import cleaning, phrases, pipeline


def phrasal_verbs(text):
    """The phrasal verbs found in a text, as (lemma, form in the text) pairs."""
    matches = phrases.find_phrasal_verbs(pipeline.parse(text))
    return [(m.candidate.lemma, m.candidate.surface_form) for m in matches]


# --- rule 1: the parser's particle ---------------------------------------------


def test_verb_and_particle_next_to_each_other():
    assert phrasal_verbs("But her neighbour, Tom, told her not to give in so easily.") == [
        ("give in", "give in")
    ]


def test_particle_followed_by_an_object():
    assert phrasal_verbs("I'll help you work out a plan.") == [("work out", "work out")]


def test_preposition_after_the_particle_is_not_swallowed():
    # "after" starts a time phrase here; there is no phrasal verb "give up after".
    assert phrasal_verbs("She nearly gave up after the third week.") == [("give up", "gave up")]
    assert phrasal_verbs("The hardest part was the decision to turn up on the first morning.") == [
        ("turn up", "turn up")
    ]


def test_particle_separated_from_the_verb_by_a_noun_phrase():
    text = (
        "So she turned her phone off every evening, laid out her running shoes, "
        "and set an alarm for six o'clock."
    )

    assert phrasal_verbs(text) == [("turn off", "turned ... off"), ("lay out", "laid out")]


def test_particle_separated_from_the_verb_by_a_pronoun():
    text = "Her friends couldn't believe it when she called them up and told them the news."

    assert phrasal_verbs(text) == [("call up", "called ... up")]


def test_same_particle_verb_joined_and_separated_in_one_sentence():
    text = (
        "When the organisers called off the winter race because of the snow, nobody was "
        "disappointed, since the committee promised to put it off until spring."
    )

    assert phrasal_verbs(text) == [("call off", "called off"), ("put off", "put ... off")]


def test_imperative_with_separated_particle():
    assert phrasal_verbs("Turn the light off.") == [("turn off", "Turn ... off")]


def test_passive_phrasal_verb():
    assert phrasal_verbs("The winter race was called off.") == [("call off", "called off")]


def test_particle_verbs_that_are_not_in_the_list_are_still_found():
    # Neither "go down" nor "walk through" is in phrasal_verbs.txt.
    # "went down" has a particle; "walked through the park" has a preposition.
    text = (
        "They walked through the park, picked the best route, "
        "and carried on until the sun went down."
    )

    assert phrasal_verbs(text) == [("carry on", "carried on"), ("go down", "went down")]


# --- rule 2: the list ----------------------------------------------------------


def test_three_part_verb_wins_over_its_two_part_beginning():
    # The parser sees "put" + particle "up"; the list knows "put up with".
    assert phrasal_verbs("Everyone put up with the cold weather.") == [
        ("put up with", "put up with")
    ]


def test_three_part_and_two_part_verbs_in_one_sentence():
    text = (
        "At first, she couldn't keep up with the others, "
        "and she nearly gave up after the third week."
    )

    assert phrasal_verbs(text) == [("keep up with", "keep up with"), ("give up", "gave up")]


def test_adverb_plus_preposition_verb():
    # spaCy calls "forward" an ordinary adverb, so only the list can find this one.
    assert phrasal_verbs("You just have to look forward to the small improvements.") == [
        ("look forward to", "look forward to")
    ]


def test_verb_with_a_preposition_and_verb_with_an_adverb():
    text = '"I ran into a lot of doubts," she admits, "but I\'m glad I didn\'t run away from them."'

    assert phrasal_verbs(text) == [("run into", "ran into"), ("run away", "run away")]


def test_verb_form_at_the_start_of_a_sentence():
    assert phrasal_verbs("Looking back, she says the hardest part was not the distance.") == [
        ("look back", "Looking back")
    ]


def test_listed_adverb_separated_from_the_verb():
    assert phrasal_verbs("She picked it up and threw it away.") == [
        ("pick up", "picked ... up"),
        ("throw away", "threw ... away"),
    ]


def test_preposition_left_at_the_end_of_a_clause():
    text = "He came across an old photo that he had been looking for."

    assert phrasal_verbs(text) == [("come across", "came across"), ("look for", "looking for")]


def test_other_three_part_verbs():
    assert phrasal_verbs("We ran out of milk, so I came up with a plan.") == [
        ("run out of", "ran out of"),
        ("come up with", "came up with"),
    ]


def test_listed_preposition_must_directly_follow_the_verb():
    # "look for" is listed, but here "for a minute" only says how long.
    assert phrasal_verbs("She looked in the mirror for a minute.") == []


def test_plain_verb_with_a_preposition_is_not_a_phrasal_verb():
    assert phrasal_verbs("Last year she moved to Manchester to start a new job.") == []


# --- literal versus idiomatic ---------------------------------------------------


def test_literal_movement_up_something_is_not_a_phrasal_verb():
    # "up the hill" is a direction; the parser marks "up" as a preposition here.
    assert phrasal_verbs("He ran up the hill.") == []


def test_look_up_a_word_is_a_phrasal_verb():
    assert phrasal_verbs("She looked up the word in a dictionary.") == [("look up", "looked up")]
    assert phrasal_verbs("He looked the word up.") == [("look up", "looked ... up")]


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: the tool recognises the form, not the meaning. In 'looked up at "
    "the sky' the verb is literal (raise your eyes), but the parser marks 'up' as a particle "
    "exactly as in 'looked up the word', so 'look up' is offered.",
)
def test_literal_look_up_at_the_sky_is_not_offered():
    assert phrasal_verbs("He ran up the hill and looked up at the sky.") == []


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: 'run into' is in the list for its idiomatic meaning (meet by "
    "chance, encounter). The list is matched on words, so literal movement into a place is "
    "offered as well.",
)
def test_literal_run_into_a_room_is_not_offered():
    assert phrasal_verbs("She ran into the kitchen.") == []


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: a later part of a listed verb only has to follow the part before "
    "it. Here 'with her brother' is a separate phrase, and the verb is 'put up' (erect), "
    "but 'put up with' (tolerate) is reported.",
)
def test_put_a_tent_up_with_someone_is_put_up():
    assert phrasal_verbs("She put the tent up with her brother.") == [("put up", "put ... up")]


# --- problems found in spoken text ------------------------------------------------


def test_preposition_before_a_date_is_not_a_phrasal_verb():
    # "take on" is in the list (take on a challenge), but here "on" introduces a date.
    assert phrasal_verbs("The photo was taken on January the 3rd.") == []
    assert phrasal_verbs("The photo was taken on Monday.") == []


def test_listed_verb_is_still_found_when_no_date_follows():
    assert phrasal_verbs("The company took on ten new workers.") == [("take on", "took on")]


def test_true_particle_before_a_date_phrase_is_kept():
    assert phrasal_verbs("They carried on in March and gave up on Friday.") == [
        ("carry on", "carried on"),
        ("give up", "gave up"),
    ]


def test_three_part_verb_look_back_on():
    assert phrasal_verbs("When we look back on that period, we see many mistakes.") == [
        ("look back on", "look back on")
    ]


def test_look_back_without_on_is_still_look_back():
    assert phrasal_verbs("Looking back, it was the right decision.") == [
        ("look back", "Looking back")
    ]


def test_three_part_verb_hold_on_to():
    assert phrasal_verbs("He is trying to hold on to power for as long as he can.") == [
        ("hold on to", "hold on to")
    ]
    assert phrasal_verbs("She held on to the rope.") == [("hold on to", "held on to")]


def test_to_of_an_infinitive_is_not_part_of_the_phrasal_verb():
    # "to see" is an infinitive here, so the verb is "hold on", not "hold on to".
    assert phrasal_verbs("Hold on to see what happens next.") == [("hold on", "Hold on")]


def test_repeated_preposition_from_speech_gives_a_false_particle_without_cleaning():
    # This is why text is cleaned before parsing (see nlp/cleaning.py).
    raw = "so what is happening in in um in Brazil right now is uh very serious"

    assert phrasal_verbs(raw) == [("happen in", "happening in")]
    assert phrasal_verbs(cleaning.clean(raw)) == []


def test_between_equally_long_matches_the_one_closer_to_the_verb_wins():
    doc = pipeline.parse("We look back on that period.")
    look, back, on = doc[1], doc[2], doc[3]

    # As if the parser had marked "on" as a particle while the list found "back".
    assert phrases.choose_match(look, [[on], [back]]) == [back]
    assert phrases.choose_match(look, [[back], [on]]) == [back]


def test_longer_match_wins_even_when_it_starts_further_away():
    doc = pipeline.parse("We look back on that period.")
    look, back, on = doc[1], doc[2], doc[3]

    assert phrases.choose_match(look, [[back], [back, on]]) == [back, on]
    assert phrases.choose_match(look, []) is None


@pytest.mark.xfail(
    strict=True,
    reason="Known limitation: 'take on' is in the list and 'on' follows the verb. The parser "
    "calls 'on' a preposition here, but it does the same in the real phrasal verb 'count on "
    "him', so the two cannot be told apart without marking each list entry as "
    "particle-type or preposition-type.",
)
def test_literal_taken_on_a_tour_is_not_offered():
    assert phrasal_verbs("She was taken on a tour of the city.") == []


# --- what a match contains -------------------------------------------------------


def test_match_describes_the_phrase_and_the_tokens_it_uses():
    doc = pipeline.parse("Turn the light off.")

    (match,) = phrases.find_phrasal_verbs(doc)

    assert match.candidate.kind is ItemKind.PHRASAL_VERB
    assert match.candidate.pos == "VERB"
    assert match.candidate.sentence == "Turn the light off."
    assert [doc[i].text for i in sorted(match.token_indexes)] == ["Turn", "off"]


# --- the list file ---------------------------------------------------------------


def test_list_format_ignores_comments_blank_lines_case_and_extra_spaces():
    text = "# a comment\n\ngive up\n  Look   Forward to  \nrun into  # trailing comment\n"

    assert phrases.parse_phrase_list(text) == ["give up", "look forward to", "run into"]


def test_shipped_list_is_well_formed():
    entries = phrases.parse_phrase_list(phrases.read_data_file("phrasal_verbs.txt"))

    assert len(entries) > 100
    assert len(entries) == len(set(entries)), "duplicate entries"
    for entry in entries:
        words = entry.split()
        assert 2 <= len(words) <= 3, entry
        assert all(word.isalpha() for word in words), entry


def test_listed_verbs_are_grouped_by_verb():
    by_verb = phrases.listed_phrasal_verbs()

    assert ("forward", "to") in by_verb["look"]
    assert ("up", "with") in by_verb["put"]
