import sqlite3

import pytest

from vocab.storage import db


def table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_new_database_gets_all_tables(conn):
    assert table_names(conn) == {
        "sources",
        "items",
        "occurrences",
        "cards",
        "srs_state",
        "reviews",
    }


def test_new_database_is_stamped_with_schema_version(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_reopening_a_file_keeps_its_data(tmp_path):
    path = tmp_path / "nested" / "vocab.db"  # the parent folder does not exist yet

    first = db.connect(path)
    with first:
        first.execute(
            "INSERT INTO items (kind, lemma, created_at) VALUES ('word', 'reluctant', '2026-01-01')"
        )
    first.close()

    second = db.connect(path)
    lemmas = [row["lemma"] for row in second.execute("SELECT lemma FROM items")]
    second.close()

    assert lemmas == ["reluctant"]


def test_database_from_a_newer_version_is_refused(tmp_path):
    path = tmp_path / "vocab.db"
    newer = sqlite3.connect(path)
    newer.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
    newer.close()

    with pytest.raises(db.DatabaseVersionError):
        db.connect(path)


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO occurrences (item_id, source_id, sentence, surface_form) "
            "VALUES (999, 999, 'No such item.', 'item')"
        )
