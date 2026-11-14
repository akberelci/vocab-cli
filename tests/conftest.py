import pytest

from vocab.storage import db


@pytest.fixture
def conn():
    """A fresh, empty database in memory for each test."""
    connection = db.connect(":memory:")
    yield connection
    connection.close()
