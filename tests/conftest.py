import json
import sys
from pathlib import Path

from jinja2 import Environment

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402  (needs ROOT on sys.path first)


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def data() -> dict[str, object]:
    return json.loads((ROOT / "data" / "resume.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def env() -> Environment:
    return build.make_env()


@pytest.fixture(scope="session")
def pages(env, data) -> dict[str, str]:
    """Freshly rendered site files, keyed by file name."""
    return {path.name: text for path, text in build.render_pages(env, data).items()}
