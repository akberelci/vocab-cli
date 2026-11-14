import pytest

from vocab import importer
from vocab.models import ItemKind, ItemStatus, Occurrence, SourceKind
from vocab.sources.base import SourceText
from vocab.sources.text_file import read_text_file
from vocab.storage import repo


def make_source(text, ref="story.txt"):
    return SourceText(kind=SourceKind.FILE, ref=ref, title="story", text=text)


def items_by_lemma(conn):
    return {item.lemma: item for item in repo.list_items(conn, ItemStatus.NEW)}


def test_import_saves_items_under_their_lemma(conn):
    importer.import_source(conn, make_source("The children were running."))

    items = items_by_lemma(conn)

    assert set(items) == {"the", "child", "be", "run"}
    assert items["child"].kind is ItemKind.WORD
    assert items["child"].pos == "NOUN"


def test_import_saves_the_example_sentence_and_original_form(conn):
    importer.import_source(conn, make_source("She doesn't like the children's games."))

    child = items_by_lemma(conn)["child"]

    assert repo.list_occurrences(conn, child.id) == [
        Occurrence(sentence="She doesn't like the children's games.", surface_form="children")
    ]


def test_different_forms_of_a_word_are_grouped_under_one_item(conn):
    importer.import_source(conn, make_source("He runs every day. Yesterday he ran twice."))

    run = items_by_lemma(conn)["run"]

    assert repo.list_occurrences(conn, run.id) == [
        Occurrence(sentence="He runs every day.", surface_form="runs"),
        Occurrence(sentence="Yesterday he ran twice.", surface_form="ran"),
    ]


def test_proper_names_and_numbers_are_not_saved(conn):
    importer.import_source(conn, make_source("Emma moved to Istanbul in 2019."))

    assert set(items_by_lemma(conn)) == {"move", "to", "in"}


def test_phrasal_verbs_are_saved_as_their_own_kind_of_item(conn):
    importer.import_source(conn, make_source("She turned her phone off and gave up."))

    items = items_by_lemma(conn)

    assert items["turn off"].kind is ItemKind.PHRASAL_VERB
    assert items["give up"].kind is ItemKind.PHRASAL_VERB
    assert not {"turn", "off", "give", "up"} & set(items)
    assert repo.list_occurrences(conn, items["turn off"].id) == [
        Occurrence(sentence="She turned her phone off and gave up.", surface_form="turned ... off")
    ]


def test_result_reports_how_much_was_found(conn):
    result = importer.import_source(conn, make_source("The dog saw the cat."))

    assert result.candidates == 5  # the, dog, see, the, cat
    assert result.new_items == 4  # "the" is one item


def test_second_source_only_adds_items_that_are_new(conn):
    importer.import_source(conn, make_source("The dog barked.", ref="one.txt"))

    result = importer.import_source(conn, make_source("The dog slept.", ref="two.txt"))

    assert result.new_items == 1  # only "sleep"
    dog = items_by_lemma(conn)["dog"]
    assert [o.sentence for o in repo.list_occurrences(conn, dog.id)] == [
        "The dog barked.",
        "The dog slept.",
    ]


def test_importing_the_same_text_twice_is_refused(conn):
    importer.import_source(conn, make_source("The dog barked.", ref="one.txt"))

    with pytest.raises(importer.AlreadyImportedError):
        importer.import_source(conn, make_source("The dog barked.", ref="renamed.txt"))


def test_known_words_stay_known_after_another_import(conn):
    importer.import_source(conn, make_source("The dog barked.", ref="one.txt"))
    dog = items_by_lemma(conn)["dog"]
    repo.set_item_status(conn, dog.id, ItemStatus.KNOWN)

    importer.import_source(conn, make_source("A dog slept.", ref="two.txt"))

    assert "dog" not in items_by_lemma(conn)
    assert [item.lemma for item in repo.list_items(conn, ItemStatus.KNOWN)] == ["dog"]


def test_a_text_file_can_be_imported_end_to_end(conn, tmp_path):
    path = tmp_path / "story.txt"
    path.write_text(
        "Emma didn't want to leave Istanbul.\nShe's lived there for 12 years.\n",
        encoding="utf-8",
    )

    result = importer.import_source(conn, read_text_file(path))

    assert result.new_items == len(items_by_lemma(conn))
    assert {"do", "not", "want", "leave", "live", "year"} <= set(items_by_lemma(conn))
    assert not {"emma", "istanbul"} & set(items_by_lemma(conn))
