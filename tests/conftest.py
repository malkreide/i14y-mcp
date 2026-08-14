"""Access to the recorded I14Y responses in `tests/fixtures/`.

A handwritten stub agrees with whatever the author expected, which is why the
suite stayed green when the source renamed a field in production. These files
are real responses, recorded by `scripts/record_fixtures.py`, each carrying the
date it was taken.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


def load_recording(name: str) -> dict[str, Any]:
    """Return the whole recording document, `_recording` metadata included."""
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        raise AssertionError(
            f"No recording named {name!r} in {FIXTURES}. "
            "Run `python scripts/record_fixtures.py` to record the fixtures."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_body(name: str) -> Any:
    """Return just the recorded response body, ready to hand to respx."""
    return load_recording(name)["body"]


def recorded_at(name: str) -> dt.datetime:
    """Return when `name` was recorded, as an aware UTC datetime."""
    stamp = load_recording(name)["_recording"]["recorded_at"]
    parsed = dt.datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def all_recordings() -> list[str]:
    """Names of every recording on disk, sorted."""
    return sorted(p.stem for p in FIXTURES.glob("*.json"))
