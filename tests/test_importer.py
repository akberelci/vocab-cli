import pytest

from vocab import importer
from vocab.models import ItemKind, ItemStatus, Occurrence, SourceKind
from vocab.sources.base import SourceText
from vocab.sources.text_file import read_text_file
from vocab.storage import repo

B2 = 4.0


def make_source(text, ref="story.txt"):
    return SourceText(kind=SourceKind.FILE, ref=ref, title="story", text=text)


def import_text(conn, text, ref="story.txt", known_zipf=B2):
    return importer.import_source(conn, make_source(text, ref), known_zipf)


def items_by_lemma(conn):
    return {item.lemma: item for item in repo.list_items(conn, ItemStatus.NEW)}


# --- what is saved -----------------------------------------------------------------


def test_import_saves_items_under_their_lemma(conn):
    import_text(conn, "The children were running.")

    items = items_by_lemma(conn)

    assert set(items) == {"the", "child", "be", "run"}
    assert items["child"].kind is ItemKind.WORD
    assert items["child"].pos == "NOUN"


def test_import_saves_the_example_sentence_and_original_form(conn):
    import_text(conn, "She doesn't like the children's games.")

    child = items_by_lemma(conn)["child"]

    assert repo.list_occurrences(conn, child.id) == [
        Occurrence(sentence="She doesn't like the children's games.", surface_form="children")
    ]


def test_different_forms_of_a_word_are_grouped_under_one_item(conn):
    import_text(conn, "He runs every day. Yesterday he ran twice.")

    run = items_by_lemma(conn)["run"]

    assert repo.list_occurrences(conn, run.id) == [
        Occurrence(sentence="He runs every day.", surface_form="runs"),
        Occurrence(sentence="Yesterday he ran twice.", surface_form="ran"),
    ]


def test_proper_names_and_numbers_are_not_saved(conn):
    import_text(conn, "Emma moved to Istanbul in 2019.")

    assert set(items_by_lemma(conn)) == {"move", "to", "in"}


def test_phrasal_verbs_are_saved_as_their_own_kind_of_item(conn):
    import_text(conn, "She turned her phone off and gave up.")

    items = items_by_lemma(conn)

    assert items["turn off"].kind is ItemKind.PHRASAL_VERB
    assert items["give up"].kind is ItemKind.PHRASAL_VERB
    assert not {"turn", "off", "give", "up"} & set(items)
    assert repo.list_occurrences(conn, items["turn off"].id) == [
        Occurrence(sentence="She turned her phone off and gave up.", surface_form="turned ... off")
    ]


def test_idioms_are_saved_as_their_own_kind_of_item(conn):
    import_text(conn, "It rained, so we called it a day.")

    idiom = items_by_lemma(conn)["call it a day"]

    assert idiom.kind is ItemKind.IDIOM
    assert idiom.pos is None
    assert repo.list_occurrences(conn, idiom.id) == [
        Occurrence(sentence="It rained, so we called it a day.", surface_form="called it a day")
    ]
    assert {"call", "day"} <= set(items_by_lemma(conn))  # the single words are kept too


# --- difficulty --------------------------------------------------------------------


def test_words_get_a_frequency_score(conn):
    import_text(conn, "The reluctant athlete finally agreed.")

    items = items_by_lemma(conn)

    assert items["the"].zipf > 7
    assert 3 < items["reluctant"].zipf < 4


def test_score_uses_the_written_form_when_it_is_more_common_than_the_lemma(conn):
    import_text(conn, "Nobody was disappointed.")

    # The lemma "disappoint" alone would be below 4.0.
    assert items_by_lemma(conn)["disappoint"].zipf >= B2


def test_phrases_have_no_frequency_score(conn):
    import_text(conn, "At first she nearly gave up.")

    items = items_by_lemma(conn)

    assert items["give up"].zipf is None
    assert items["at first"].zipf is None


def test_word_unknown_to_wordfreq_is_saved_without_a_score(conn):
    result = import_text(conn, "The machine began to zxqvorble loudly.")

    assert items_by_lemma(conn)["zxqvorble"].zipf is None
    assert result.unscored == 1


def test_everything_is_saved_even_when_it_is_too_easy(conn):
    # Easy words stay in the database, so a lower threshold later still finds them.
    import_text(conn, "The dog saw the cat.")

    assert set(items_by_lemma(conn)) == {"the", "dog", "see", "cat"}


# --- the summary -------------------------------------------------------------------


def test_summary_separates_candidates_from_easy_words(conn):
    result = import_text(conn, "At first the reluctant athlete gave up.")

    # reluctant (3.8) is a candidate; at, first, the, athlete are too easy at 4.0.
    assert result.new_words == 1
    assert result.new_phrasal_verbs == 1  # give up
    assert result.new_idioms == 1  # at first
    assert result.too_easy == 4
    assert result.new_candidates == 3
    assert result.total == 7
    assert result.unscored == 0


def test_summary_counts_distinct_items_not_repeats(conn):
    result = import_text(conn, "The dog saw the cat. The cat saw the dog.")

    assert result.total == 4  # the, dog, see, cat


def test_phrases_are_candidates_whatever_the_threshold(conn):
    result = import_text(conn, "She gave up.", known_zipf=0.0)

    # With a threshold of 0 every scored word is "too easy", but not the phrasal verb.
    assert result.new_phrasal_verbs == 1
    assert result.new_words == 0
    assert result.too_easy == 1  # she


def test_looser_threshold_offers_more_words(conn):
    text = "The reluctant athlete found it worthwhile."

    at_b1 = import_text(conn, text, known_zipf=4.5)

    assert at_b1.new_words == 3  # reluctant, athlete, worthwhile


def test_second_import_reports_items_seen_before(conn):
    import_text(conn, "The reluctant dog gave up.", ref="one.txt")

    result = import_text(conn, "A reluctant cat gave up and slept.", ref="two.txt")

    assert result.seen_before == 2  # reluctant, give up
    assert result.new_candidates == 0
    reluctant = items_by_lemma(conn)["reluctant"]
    assert [o.sentence for o in repo.list_occurrences(conn, reluctant.id)] == [
        "The reluctant dog gave up.",
        "A reluctant cat gave up and slept.",
    ]


def test_items_marked_known_are_counted_as_skipped(conn):
    import_text(conn, "The reluctant dog gave up.", ref="one.txt")
    for lemma in ("reluctant", "give up"):
        repo.set_item_status(conn, items_by_lemma(conn)[lemma].id, ItemStatus.KNOWN)

    result = import_text(conn, "A reluctant cat gave up.", ref="two.txt")

    assert result.known_or_ignored == 2
    assert result.seen_before == 0
    assert result.new_candidates == 0


def test_known_words_stay_known_after_another_import(conn):
    import_text(conn, "The dog barked.", ref="one.txt")
    repo.set_item_status(conn, items_by_lemma(conn)["dog"].id, ItemStatus.KNOWN)

    import_text(conn, "A dog slept.", ref="two.txt")

    assert "dog" not in items_by_lemma(conn)
    assert [item.lemma for item in repo.list_items(conn, ItemStatus.KNOWN)] == ["dog"]


# --- repeated imports and files --------------------------------------------------------


def test_importing_the_same_text_twice_is_refused(conn):
    import_text(conn, "The dog barked.", ref="one.txt")

    with pytest.raises(importer.AlreadyImportedError):
        import_text(conn, "The dog barked.", ref="renamed.txt")


def test_a_text_file_can_be_imported_end_to_end(conn, tmp_path):
    path = tmp_path / "story.txt"
    path.write_text(
        "Emma didn't want to leave Istanbul.\nShe's lived there for 12 years.\n",
        encoding="utf-8",
    )

    result = importer.import_source(conn, read_text_file(path), B2)

    assert result.total == len(items_by_lemma(conn))
    assert {"do", "not", "want", "leave", "live", "year"} <= set(items_by_lemma(conn))
    assert not {"emma", "istanbul"} & set(items_by_lemma(conn))
