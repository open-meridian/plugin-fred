"""FRED's answers kept as received, where each rate was first read, and
months moved past their window."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fred.api import Fetched, observations_path, series_path
from fred.raw import RawStore, name_of

from conftest import AT


def fetched(at: Any, path: str = "") -> Fetched:
    path = path or observations_path("SOFR", date(2026, 10, 12), date(2026, 10, 22))
    return Fetched(path, 200, b'{"observations": []}', at)


def test_an_answer_kept_and_read_back(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    key = store.keep(fetched(AT))
    assert (
        key
        == "responses/2026-10/20261023T140000000000Z-SOFR-observations-20261012-20261022.json.gz"
    )
    kept = store.read(key)
    assert kept is not None and kept["status"] == 200
    assert kept["body"] == '{"observations": []}'
    assert kept["url"].startswith("https://api.stlouisfed.org/fred/series/observations?")
    assert "api_key" not in kept["url"]
    assert store.read("../outside.json.gz") is None
    assert name_of(series_path("DGS10")) == "DGS10-series"
    assert name_of("/elsewhere") == "answer-answer"


def test_a_rate_names_the_answer_it_was_first_read_from(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    one, two = store.keep(fetched(AT)), store.keep(fetched(AT + timedelta(hours=1)))
    day = date(2026, 10, 22)
    first, noted = store.first("row", day, "3.90", one, 7)
    assert noted and first.key == one and first.published_ns == 7
    again, noted = store.first("row", day, "3.90", two, 9)
    assert not noted and again.key == one and again.published_ns == 7
    # A revised value is noted afresh, naming the answer that revised it.
    revised, noted = store.first("row", day, "3.91", two, 9)
    assert noted and revised.key == two and revised.published_ns == 9
    store.save_firsts()
    later = RawStore(tmp_path)
    assert later.first("row", day, "3.90", two, 0) == (first, False)


def test_months_past_the_window_are_moved(tmp_path: Path) -> None:
    class Plugin:
        stored: list[Any] = []

        def __init__(self) -> None:
            self.archived: list[str] = []

        async def archive_unit(self, kind: str, unit: str, **_: Any) -> None:
            self.archived.append(unit)

        async def delete_unit(self, kind: str, unit: str, **_: Any) -> None:
            raise AssertionError("not asked")

    store = RawStore(tmp_path)
    store.granted = True
    store.keep(fetched(AT - timedelta(days=400)))
    store.keep(fetched(AT))
    plugin = Plugin()
    done = asyncio.run(store.tend(plugin, 365, "archived", AT))  # type: ignore[arg-type]
    assert done["archived"] == 1 and plugin.archived == ["responses/2025-09"]
    assert plugin.stored[0].record_count == 2
