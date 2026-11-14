"""Difficulty scoring with the real wordfreq data.

The tests compare scores with each other or with a threshold instead of
checking exact numbers, so they describe behaviour rather than the data file.
"""

from vocab import difficulty

B2 = 4.0


def test_common_words_score_higher_than_rare_ones():
    the = difficulty.zipf_score("the")
    decision = difficulty.zipf_score("decision")
    reluctant = difficulty.zipf_score("reluctant")
    obfuscate = difficulty.zipf_score("obfuscate")

    assert the > decision > reluctant > obfuscate


def test_scores_are_on_the_zipf_scale():
    assert 7 < difficulty.zipf_score("the") < 8
    assert 1 < difficulty.zipf_score("obfuscate") < 3


def test_lemma_alone_can_look_rarer_than_the_word_really_is():
    # "disappoint" as a bare form is uncommon; almost everybody meets it as "disappointed".
    assert difficulty.zipf_score("disappoint") < B2
    assert difficulty.zipf_score("disappointed") >= B2


def test_score_is_the_highest_of_lemma_and_written_forms():
    lemma_only = difficulty.zipf_score("disappoint")
    with_form = difficulty.zipf_score("disappoint", forms=["disappointed"])

    assert with_form == difficulty.zipf_score("disappointed")
    assert with_form > lemma_only
    assert difficulty.is_too_easy(with_form, B2)


def test_a_rarer_written_form_does_not_lower_the_score():
    assert difficulty.zipf_score("run", forms=["outran"]) == difficulty.zipf_score("run")


def test_written_form_rescues_a_strange_lemma():
    # spaCy lemmatizes "data" as "datum", which is a rare word.
    assert difficulty.zipf_score("datum") < B2
    assert difficulty.zipf_score("datum", forms=["data"]) > 5


def test_capital_letters_do_not_matter():
    assert difficulty.zipf_score("Reluctant") == difficulty.zipf_score("reluctant")
    assert difficulty.zipf_score("run", forms=["RUNNING"]) == difficulty.zipf_score("run")


def test_word_that_wordfreq_does_not_know_has_no_score():
    assert difficulty.zipf_score("asdfghjkl") is None
    assert difficulty.zipf_score("asdfghjkl", forms=["qwrtzpsd"]) is None


def test_known_limitation_common_typos_have_a_score_like_real_words():
    # wordfreq was built from real text, which contains typos. They cannot be
    # told apart from rare words by frequency. See docs/KNOWN_ISSUES.md.
    assert difficulty.zipf_score("recieve") is not None


def test_known_limitation_british_spelling_scores_lower_than_american():
    # See docs/KNOWN_ISSUES.md.
    assert difficulty.zipf_score("neighbour") < B2 <= difficulty.zipf_score("neighbor")


# --- is_too_easy -----------------------------------------------------------------


def test_word_at_or_above_the_threshold_is_too_easy():
    assert difficulty.is_too_easy(4.0, known_zipf=4.0)
    assert difficulty.is_too_easy(5.3, known_zipf=4.0)


def test_word_below_the_threshold_is_not_too_easy():
    assert not difficulty.is_too_easy(3.99, known_zipf=4.0)


def test_word_without_a_score_is_never_too_easy():
    assert not difficulty.is_too_easy(None, known_zipf=4.0)
    assert not difficulty.is_too_easy(None, known_zipf=0.0)


def test_threshold_decides_which_real_words_are_offered():
    worthwhile = difficulty.zipf_score("worthwhile")  # between 3.5 and 4.0

    assert not difficulty.is_too_easy(worthwhile, known_zipf=4.0)  # B2: offered
    assert difficulty.is_too_easy(worthwhile, known_zipf=3.5)  # C1: skipped
