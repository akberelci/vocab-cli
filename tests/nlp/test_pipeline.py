"""Sentence splitting on real English text, especially around quotation marks."""

from vocab.nlp import pipeline


def sentences(text):
    return [pipeline.sentence_text(sentence) for sentence in pipeline.parse(text).sents]


def test_plain_sentences_are_split_at_full_stops():
    assert sentences("The dog barked. A cat ran away. Nobody cared.") == [
        "The dog barked.",
        "A cat ran away.",
        "Nobody cared.",
    ]


def test_closing_quote_at_the_end_of_a_paragraph_stays_with_its_sentence():
    text = (
        '"Don\'t worry," he said. "I\'ll help you work out a plan. '
        'You just have to look forward to the small improvements."\n'
        "\n"
        "So she turned her phone off every evening."
    )

    assert sentences(text) == [
        '"Don\'t worry," he said.',
        "\"I'll help you work out a plan.",
        'You just have to look forward to the small improvements."',
        "So she turned her phone off every evening.",
    ]


def test_interrupted_quote_at_the_end_of_a_paragraph_keeps_its_closing_mark():
    text = (
        '"I ran into a lot of doubts," she admits, "but I\'m glad I didn\'t run away."\n'
        "\n"
        "He ran up the hill."
    )

    assert sentences(text) == [
        '"I ran into a lot of doubts," she admits, "but I\'m glad I didn\'t run away."',
        "He ran up the hill.",
    ]


def test_opening_quote_stays_at_the_start_of_its_own_sentence():
    assert sentences('He left early. "Why now?" she asked.') == [
        "He left early.",
        '"Why now?" she asked.',
    ]


def test_paragraph_that_starts_with_a_quote_keeps_its_opening_mark():
    text = 'She waited.\n\n"Are you coming?" he asked.'

    assert sentences(text) == ["She waited.", '"Are you coming?" he asked.']


def test_typographic_quotes_are_handled_like_plain_ones():
    text = "“Don’t worry,” he said. “It’s nearly over.”\n\nShe didn’t answer."

    assert sentences(text) == [
        "“Don't worry,” he said.",
        "“It's nearly over.”",
        "She didn't answer.",
    ]


def test_blank_line_ends_a_sentence_even_without_a_full_stop():
    # A heading has no full stop, but it is not part of the paragraph below it.
    text = "Chapter One\n\nThe rain had stopped by the time she arrived."

    assert sentences(text) == ["Chapter One", "The rain had stopped by the time she arrived."]


def test_single_line_break_does_not_end_a_sentence():
    assert sentences("The old man walked slowly\nalong the empty beach.") == [
        "The old man walked slowly along the empty beach."
    ]
