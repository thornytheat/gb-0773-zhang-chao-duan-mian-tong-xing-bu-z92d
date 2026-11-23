import pytest

from app.flow import calculate
from app.main import create_app
from app.source import load_sources


@pytest.fixture
def client(tmp_path):
    return create_app(tmp_path / 'tide.sqlite3').test_client()


@pytest.fixture
def sources():
    return load_sources({'sample': 'dirty'})


@pytest.fixture
def case(sources):
    return calculate(sources)
