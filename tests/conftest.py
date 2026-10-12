import json
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
FIX = os.path.join(HERE, "fixtures")


@pytest.fixture
def reg(tmp_path):
    """A copy of the fixture registry in a temp dir: entries.jsonl, claims, one certificate."""
    shutil.copytree(FIX, tmp_path / "reg")
    return tmp_path / "reg"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]
