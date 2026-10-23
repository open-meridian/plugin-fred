"""FRED's API as asked: the key added only as a request is sent, and never
kept, logged or said; FRED's refusals in its own words; the stand-in
answering a range from the recording."""

from __future__ import annotations

import asyncio
import email.message
import io
import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any

import pytest

from fred import api as fred
from fred.classes import class_of, dataset_of

KEY = "abcdef0123456789abcdef0123456789"


class Answer(io.BytesIO):
    status = 200

    def __enter__(self) -> Answer:
        return self

    def __exit__(self, *_: Any) -> None:
        return None


def test_the_key_is_sent_and_never_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []

    def urlopen(request: urllib.request.Request, timeout: float) -> Answer:
        asked.append(request.full_url)
        return Answer(json.dumps({"echo": request.full_url}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    live = fred.LiveApi(KEY)
    got = asyncio.run(live.get(fred.series_path("SOFR")))
    assert asked == [f"{fred.BASE}/fred/series?series_id=SOFR&file_type=json&api_key={KEY}"]
    assert KEY not in got.path and KEY not in got.url and KEY not in got.text
    assert "***" in got.text


def test_a_refusal_in_freds_words_never_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def urlopen(request: urllib.request.Request, timeout: float) -> Answer:
        said = {
            "error_code": 400,
            "error_message": f"Bad Request.  The key {KEY} is not registered.",
        }
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            email.message.Message(),
            io.BytesIO(json.dumps(said).encode()),
        )

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    got = asyncio.run(fred.LiveApi(KEY).get(fred.tags_path("SOFR")))
    assert got.status == 400 and KEY not in got.error
    assert got.error == "Bad Request.  The key *** is not registered."


def test_unreachable_says_no_address(monkeypatch: pytest.MonkeyPatch) -> None:
    def urlopen(request: urllib.request.Request, timeout: float) -> Answer:
        raise urllib.error.URLError(OSError(f"no route to {request.full_url}"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(fred.Unreachable) as failed:
        asyncio.run(fred.LiveApi(KEY).get(fred.series_path("SOFR")))
    assert KEY not in str(failed.value)


def test_without_a_key_nothing_is_sent() -> None:
    with pytest.raises(fred.NoKey):
        asyncio.run(fred.LiveApi("").get(fred.series_path("SOFR")))


def test_the_stand_in_answers_a_range_and_refuses_an_unknown_series() -> None:
    api = fred.SyntheticApi()
    got = asyncio.run(
        api.get(fred.observations_path("DGS10", date(2026, 10, 19), date(2026, 10, 21)))
    )
    answer = got.json()
    assert [o["date"] for o in answer["observations"]] == ["2026-10-19", "2026-10-20", "2026-10-21"]
    assert answer["count"] == 3 and all(isinstance(o["value"], str) for o in answer["observations"])
    refused = asyncio.run(api.get(fred.series_path("NOSUCH")))
    assert refused.status == 400 and refused.error == "Bad Request.  The series does not exist."
    assert api.today(None) == date(2026, 10, 22)  # type: ignore[arg-type]


def test_each_class_is_a_dataset() -> None:
    def tagged(*names: str) -> dict[str, Any]:
        return {"tags": [{"name": n, "group_id": "cc"} for n in names]}

    assert class_of(tagged("public domain: citation requested")) == "public"
    assert class_of(tagged("Copyrighted: Citation Required")) == "cited"
    assert class_of(tagged("copyrighted: citation required",
                           "copyrighted: pre-approval required")) == "restricted"  # fmt: skip
    assert class_of({"tags": [{"name": "daily", "group_id": "freq"}]}) == ""
    assert [dataset_of(c) for c in ("public", "cited", "restricted", "")] == [
        "fred_public", "fred_cited", "fred_restricted", ""
    ]  # fmt: skip
    # Every series carried is classed in the recording.
    api = fred.SyntheticApi()
    assert {class_of(t) for t in api.tags.values()} == {"public", "cited"}
