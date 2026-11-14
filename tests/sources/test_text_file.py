import pytest

from vocab.models import SourceKind
from vocab.sources.base import SourceText
from vocab.sources.text_file import SourceError, read_text_file


def test_reads_text_and_uses_the_file_name_as_title(tmp_path):
    path = tmp_path / "short-story.txt"
    path.write_text("She gave up smoking.", encoding="utf-8")

    source = read_text_file(path)

    assert source.kind is SourceKind.FILE
    assert source.text == "She gave up smoking."
    assert source.title == "short-story"
    assert source.ref == str(path.resolve())


def test_reads_non_ascii_characters(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("A naïve café owner said “hello”.", encoding="utf-8")

    assert read_text_file(path).text == "A naïve café owner said “hello”."


def test_removes_the_byte_order_mark(tmp_path):
    path = tmp_path / "windows.txt"
    path.write_bytes(b"\xef\xbb\xbfHello there.")

    assert read_text_file(path).text == "Hello there."


def test_missing_file_gives_a_readable_error(tmp_path):
    with pytest.raises(SourceError, match="File not found"):
        read_text_file(tmp_path / "missing.txt")


def test_directory_gives_a_readable_error(tmp_path):
    with pytest.raises(SourceError, match="Not a file"):
        read_text_file(tmp_path)


def test_binary_file_gives_a_readable_error(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")

    with pytest.raises(SourceError, match="Not a UTF-8 text file"):
        read_text_file(path)


def test_empty_file_gives_a_readable_error(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  \n\n", encoding="utf-8")

    with pytest.raises(SourceError, match="File is empty"):
        read_text_file(path)


def test_same_text_has_the_same_hash_regardless_of_where_it_came_from():
    first = SourceText(SourceKind.FILE, "a.txt", "a", "Hello there.")
    renamed = SourceText(SourceKind.FILE, "b.txt", "b", "Hello there.")
    different = SourceText(SourceKind.FILE, "a.txt", "a", "Hello again.")

    assert first.content_hash == renamed.content_hash
    assert first.content_hash != different.content_hash
