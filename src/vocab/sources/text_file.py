"""Reading a plain text file."""

from pathlib import Path

from vocab.models import SourceKind
from vocab.sources.base import SourceText


class SourceError(Exception):
    """A source could not be read. The message is meant to be shown to the user."""


def read_text_file(path: Path | str) -> SourceText:
    """Read a UTF-8 text file. The file name (without extension) becomes the title."""
    path = Path(path)

    try:
        # "utf-8-sig" reads normal UTF-8 and also removes the invisible marker
        # (BOM) that some Windows editors put at the start of a file.
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise SourceError(f"File not found: {path}") from None
    except IsADirectoryError:
        raise SourceError(f"Not a file: {path}") from None
    except UnicodeDecodeError:
        raise SourceError(f"Not a UTF-8 text file: {path}") from None

    if not text.strip():
        raise SourceError(f"File is empty: {path}")

    return SourceText(
        kind=SourceKind.FILE,
        ref=str(path.resolve()),
        title=path.stem,
        text=text,
    )
