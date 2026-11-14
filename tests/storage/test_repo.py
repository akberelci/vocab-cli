import sqlite3

import pytest

from vocab.models import ItemKind, ItemStatus, Occurrence, SourceKind
from vocab.storage import repo


@pytest.fixture
def source_id(conn):
    return repo.add_source(conn, SourceKind.FILE, "story.txt", "A story", "hash-1")


# --- sources -----------------------------------------------------------------


def test_source_can_be_found_by_its_hash(conn, source_id):
    assert repo.find_source_by_hash(conn, "hash-1") == source_id


def test_unknown_hash_is_not_found(conn):
    assert repo.find_source_by_hash(conn, "never-imported") is None


def test_same_content_cannot_be_imported_twice(conn, source_id):
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_source(conn, SourceKind.FILE, "copy-of-story.txt", None, "hash-1")


@pytest.mark.parametrize("kind", list(SourceKind))
def test_schema_accepts_every_source_kind(conn, kind):
    repo.add_source(conn, kind, "ref", None, f"hash-{kind}")


# --- items -------------------------------------------------------------------


def test_new_item_starts_with_status_new(conn):
    repo.upsert_item(conn, ItemKind.WORD, "reluctant", pos="ADJ", zipf=3.9)

    (item,) = repo.list_items(conn, ItemStatus.NEW)

    assert item.lemma == "reluctant"
    assert item.kind is ItemKind.WORD
    assert item.pos == "ADJ"
    assert item.zipf == 3.9
    assert item.status is ItemStatus.NEW


def test_upserting_the_same_item_twice_returns_the_same_id(conn):
    first = repo.upsert_item(conn, ItemKind.WORD, "reluctant")
    second = repo.upsert_item(conn, ItemKind.WORD, "reluctant")

    assert first == second
    assert len(repo.list_items(conn, ItemStatus.NEW)) == 1


def test_same_lemma_with_different_kind_is_a_different_item(conn):
    # "give up" could in theory be listed as a phrasal verb and as an idiom.
    as_phrasal_verb = repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    as_idiom = repo.upsert_item(conn, ItemKind.IDIOM, "give up")

    assert as_phrasal_verb != as_idiom


def test_upsert_does_not_reset_the_status_of_an_existing_item(conn):
    item_id = repo.upsert_item(conn, ItemKind.WORD, "house")
    repo.set_item_status(conn, item_id, ItemStatus.KNOWN)

    repo.upsert_item(conn, ItemKind.WORD, "house")  # seen again in a later import

    assert repo.list_items(conn, ItemStatus.NEW) == []
    assert [item.lemma for item in repo.list_items(conn, ItemStatus.KNOWN)] == ["house"]


def test_list_items_filters_by_status_and_sorts_alphabetically(conn):
    repo.upsert_item(conn, ItemKind.WORD, "wander")
    repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    ignored = repo.upsert_item(conn, ItemKind.WORD, "london")
    repo.set_item_status(conn, ignored, ItemStatus.IGNORED)

    lemmas = [item.lemma for item in repo.list_items(conn, ItemStatus.NEW)]

    assert lemmas == ["give up", "wander"]


@pytest.mark.parametrize("kind", list(ItemKind))
def test_schema_accepts_every_item_kind(conn, kind):
    repo.upsert_item(conn, kind, "example")


@pytest.mark.parametrize("status", list(ItemStatus))
def test_schema_accepts_every_item_status(conn, status):
    item_id = repo.upsert_item(conn, ItemKind.WORD, "example")
    repo.set_item_status(conn, item_id, status)

    assert len(repo.list_items(conn, status)) == 1


def test_schema_rejects_an_unknown_status(conn):
    item_id = repo.upsert_item(conn, ItemKind.WORD, "example")

    with pytest.raises(sqlite3.IntegrityError):
        repo.set_item_status(conn, item_id, "mastered")


# --- occurrences -------------------------------------------------------------


def test_occurrences_are_returned_in_the_order_they_were_added(conn, source_id):
    item_id = repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    repo.add_occurrence(conn, item_id, source_id, "She gave up smoking.", "gave up")
    repo.add_occurrence(conn, item_id, source_id, "Don't give it up yet.", "give up")

    assert repo.list_occurrences(conn, item_id) == [
        Occurrence(sentence="She gave up smoking.", surface_form="gave up"),
        Occurrence(sentence="Don't give it up yet.", surface_form="give up"),
    ]


def test_same_sentence_is_stored_only_once_per_item_and_source(conn, source_id):
    item_id = repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    repo.add_occurrence(conn, item_id, source_id, "She gave up smoking.", "gave up")
    repo.add_occurrence(conn, item_id, source_id, "She gave up smoking.", "gave up")

    assert len(repo.list_occurrences(conn, item_id)) == 1


def test_changes_are_rolled_back_when_an_import_fails(conn, source_id):
    conn.commit()  # the source from the fixture is saved

    with pytest.raises(sqlite3.IntegrityError), conn:
        repo.upsert_item(conn, ItemKind.WORD, "reluctant")
        repo.add_source(conn, SourceKind.FILE, "story.txt", None, "hash-1")  # duplicate

    assert repo.list_items(conn, ItemStatus.NEW) == []


# --- finding items -------------------------------------------------------------


def test_find_item_returns_the_item_or_none(conn):
    repo.upsert_item(conn, ItemKind.WORD, "reluctant", pos="ADJ", zipf=3.81)

    found = repo.find_item(conn, ItemKind.WORD, "reluctant")

    assert (found.lemma, found.pos, found.zipf) == ("reluctant", "ADJ", 3.81)
    assert repo.find_item(conn, ItemKind.IDIOM, "reluctant") is None
    assert repo.find_item(conn, ItemKind.WORD, "missing") is None


def test_find_items_by_lemma_returns_every_kind(conn):
    repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    repo.upsert_item(conn, ItemKind.IDIOM, "give up")
    repo.upsert_item(conn, ItemKind.WORD, "give")

    assert {item.kind for item in repo.find_items_by_lemma(conn, "give up")} == {
        ItemKind.PHRASAL_VERB,
        ItemKind.IDIOM,
    }
    assert repo.find_items_by_lemma(conn, "missing") == []


# --- candidates ----------------------------------------------------------------


@pytest.fixture
def mixed_items(conn):
    repo.upsert_item(conn, ItemKind.WORD, "the", zipf=7.73)
    repo.upsert_item(conn, ItemKind.WORD, "athlete", zipf=4.11)
    repo.upsert_item(conn, ItemKind.WORD, "reluctant", zipf=3.81)
    repo.upsert_item(conn, ItemKind.WORD, "obfuscate", zipf=2.28)
    repo.upsert_item(conn, ItemKind.WORD, "zxqvorble", zipf=None)
    repo.upsert_item(conn, ItemKind.PHRASAL_VERB, "give up")
    repo.upsert_item(conn, ItemKind.IDIOM, "at first")


def test_word_candidates_are_below_the_threshold_rarest_first(conn, mixed_items):
    lemmas = [item.lemma for item in repo.list_word_candidates(conn, known_zipf=4.0)]

    # Words without a score come last: we cannot rank them.
    assert lemmas == ["obfuscate", "reluctant", "zxqvorble"]


def test_word_exactly_at_the_threshold_is_not_a_candidate(conn, mixed_items):
    lemmas = [item.lemma for item in repo.list_word_candidates(conn, known_zipf=4.11)]

    assert "athlete" not in lemmas


def test_changing_the_threshold_changes_the_candidates_without_a_new_import(conn, mixed_items):
    assert repo.count_word_candidates(conn, known_zipf=4.0) == 3
    assert repo.count_word_candidates(conn, known_zipf=4.5) == 4  # + athlete
    assert repo.count_word_candidates(conn, known_zipf=3.5) == 2  # - reluctant


def test_word_candidates_can_be_limited(conn, mixed_items):
    lemmas = [item.lemma for item in repo.list_word_candidates(conn, known_zipf=4.0, limit=2)]

    assert lemmas == ["obfuscate", "reluctant"]


def test_phrase_candidates_ignore_the_threshold(conn, mixed_items):
    lemmas = [item.lemma for item in repo.list_phrase_candidates(conn)]

    assert lemmas == ["at first", "give up"]
    assert repo.count_phrase_candidates(conn) == 2
    assert len(repo.list_phrase_candidates(conn, limit=1)) == 1


@pytest.mark.parametrize("status", [ItemStatus.KNOWN, ItemStatus.IGNORED, ItemStatus.LEARNING])
def test_items_that_are_not_new_are_not_candidates(conn, mixed_items, status):
    for kind, lemma in [(ItemKind.WORD, "reluctant"), (ItemKind.PHRASAL_VERB, "give up")]:
        repo.set_item_status(conn, repo.find_item(conn, kind, lemma).id, status)

    assert "reluctant" not in [i.lemma for i in repo.list_word_candidates(conn, known_zipf=4.0)]
    assert [i.lemma for i in repo.list_phrase_candidates(conn)] == ["at first"]
