from vocab import importer, known
from vocab.known import Outcome
from vocab.models import ItemKind, ItemStatus, SourceKind
from vocab.sources.base import SourceText
from vocab.storage import repo


def import_text(conn, text):
    source = SourceText(kind=SourceKind.FILE, ref="story.txt", title="story", text=text)
    importer.import_source(conn, source, known_zipf=4.0)


def status_of(conn, kind, lemma):
    return repo.find_item(conn, kind, lemma).status


def test_marking_an_imported_word(conn):
    import_text(conn, "The reluctant athlete agreed.")

    assert known.mark_known(conn, "reluctant") is Outcome.MARKED
    assert status_of(conn, ItemKind.WORD, "reluctant") is ItemStatus.KNOWN


def test_marking_an_imported_phrasal_verb(conn):
    import_text(conn, "She gave up.")

    assert known.mark_known(conn, "give up") is Outcome.MARKED
    assert status_of(conn, ItemKind.PHRASAL_VERB, "give up") is ItemStatus.KNOWN


def test_capital_letters_and_extra_spaces_are_ignored(conn):
    import_text(conn, "She gave up.")

    assert known.mark_known(conn, "  Give   UP ") is Outcome.MARKED


def test_marking_twice_changes_nothing(conn):
    import_text(conn, "The reluctant athlete agreed.")
    known.mark_known(conn, "reluctant")

    assert known.mark_known(conn, "reluctant") is Outcome.ALREADY


def test_word_never_seen_is_added_as_known_so_later_imports_skip_it(conn):
    assert known.mark_known(conn, "reluctant") is Outcome.CREATED

    item = repo.find_item(conn, ItemKind.WORD, "reluctant")
    assert item.status is ItemStatus.KNOWN
    assert 3 < item.zipf < 4

    import_text(conn, "The reluctant athlete agreed.")
    assert status_of(conn, ItemKind.WORD, "reluctant") is ItemStatus.KNOWN


def test_phrase_never_seen_is_not_found(conn):
    assert known.mark_known(conn, "give up") is Outcome.NOT_FOUND
    assert repo.count_items(conn) == 0


def test_empty_text_is_not_found(conn):
    assert known.mark_known(conn, "   ") is Outcome.NOT_FOUND


def test_undo_makes_the_item_a_candidate_again(conn):
    import_text(conn, "The reluctant athlete agreed.")
    known.mark_known(conn, "reluctant")

    assert known.unmark_known(conn, "reluctant") is Outcome.UNMARKED
    assert status_of(conn, ItemKind.WORD, "reluctant") is ItemStatus.NEW


def test_undo_on_an_item_that_is_not_known_changes_nothing(conn):
    import_text(conn, "The reluctant athlete agreed.")

    assert known.unmark_known(conn, "reluctant") is Outcome.ALREADY


def test_undo_on_an_unknown_item_is_not_found(conn):
    assert known.unmark_known(conn, "reluctant") is Outcome.NOT_FOUND
