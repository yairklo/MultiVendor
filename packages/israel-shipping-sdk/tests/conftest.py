import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture():
    def _load(*path_parts: str):
        with open(FIXTURES_DIR.joinpath(*path_parts), encoding="utf-8") as f:
            return json.load(f)

    return _load
