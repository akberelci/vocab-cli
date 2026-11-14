"""What every source produces, no matter where the text came from."""

import hashlib
from dataclasses import dataclass

from vocab.models import SourceKind


@dataclass(frozen=True)
class SourceText:
    kind: SourceKind
    ref: str  # where it came from: a file path or a URL
    title: str | None
    text: str

    @property
    def content_hash(self) -> str:
        """A fingerprint of the text, used to notice a repeated import.

        The same text gives the same hash even if the file was renamed or moved.
        """
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()
