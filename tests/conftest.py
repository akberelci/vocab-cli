import pytest

from vocab import config
from vocab.storage import db


@pytest.fixture(autouse=True)
def isolated_folders(tmp_path, monkeypatch):
    """Point vocab's settings and data folders at a temporary directory.

    autouse=True applies this to every test automatically, so no test can read
    or change the real ~/.config/vocab or ~/.local/share/vocab.
    """
    monkeypatch.setenv("VOCAB_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("VOCAB_DATA_DIR", str(tmp_path / "data"))
    assert tmp_path in config.config_path().parents
    assert tmp_path in config.database_path().parents


@pytest.fixture
def conn():
    """A fresh, empty database in memory for each test."""
    connection = db.connect(":memory:")
    yield connection
    connection.close()
