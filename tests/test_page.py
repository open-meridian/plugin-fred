"""The two pages under Manage, and their read tools: what each shows, to
whom, that a tool answers what its page shows, and that the key's value is
never shown."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from meridian.testing import PageClient

from fred import page as page_module
from fred.api import LiveApi
from fred.page import CONNECTION, DATASETS, figures, hold, pages
from fred.series import CARRIED, ESTR, SOFR, SUBJECTS

from conftest import CITED, PUBLIC, feed, lake, record_id, want

KEY = "abcdef0123456789abcdef0123456789"


@pytest.fixture
def client(tmp_path: Path) -> PageClient:
    work = feed(tmp_path, kept=["SOFR", "DGS10", "SOFRINDEX"])

    async def run() -> None:
        await work.check()
        await work.on_want(want("w-0924", [record_id(SOFR)], day="2026-09-24", dataset=CITED))
        await work.on_want(want("w-standing", [record_id(ESTR)], standing=True))

    asyncio.run(run())
    hold(work)
    return PageClient(pages)


def test_each_page_is_managed_alone(client: PageClient) -> None:
    served = {(r.page.path, r.level): r.response.status for r in client.every_page()}
    assert served == {
        (CONNECTION, "admin"): 200,
        (CONNECTION, "write"): 403,
        (CONNECTION, "read"): 403,
        (DATASETS, "admin"): 200,
        (DATASETS, "write"): 403,
        (DATASETS, "read"): 403,
    }
    # No rate on any page: rates are the reading roles' to show.
    client.assert_no_account_data("3.90", "5.13", "1.26384966", "2.442")


def test_connection_says_how_fred_is_reached(client: PageClient) -> None:
    text = client.get(CONNECTION, "admin").text
    assert text.index("<h2>Key</h2>") < text.index("<h2>Limits and use</h2>")
    assert text.index("<h2>Key</h2>") < text.index("<tr data-sources>") < text.index("<h2>Limits")
    # FRED is polled: no session, so no Sessions section.
    assert "<h2>Sessions</h2>" not in text
    assert 'state="ok"' in text and "Sample data" in text
    assert "FRED API key: not set" in text and "Does not stream" in text
    assert "New York Fed reference rates" in text and "Treasury par yield curves (H.15)" in text
    assert "Thu 22 Oct 2026" in text  # the latest day read
    assert "Kept current: 4 series" in text  # the three listed, and €STR's standing want
    assert 'href="/.meridian/ui/0.13.0/meridian.css"' in text


def test_datasets_lists_the_three_datasets_records_and_series(client: PageClient) -> None:
    text = client.get(DATASETS, "admin").text
    # The role's sections and FRED's as tabs, in the role's order, Served first.
    tabs = ["Served <span", "Wants <span", "Records <span", "FRED series <span", ">Terms</a>"]
    assert [text.index(t) for t in tabs] == sorted(text.index(t) for t in tabs)
    assert text.index("<h2>Served</h2>") < text.index('<th class="wide-only">Lag</th>')
    assert text.index("<h2>Served</h2>") < text.index("<h2>Subjects</h2>")
    assert "<h2>Wants</h2>" not in text
    wants = client.get(DATASETS, "admin", view="wants").text
    assert "w-standing" not in text and "Kept current" in wants
    for dataset in ("fred:fred_public", "fred:fred_cited", "fred:fred_restricted"):
        assert dataset in text
    assert "served, not kept; no derived use; display" in text
    text = client.get(DATASETS, "admin", view="records").text
    assert text.count("<tr data-record=") == len(SUBJECTS) and "<tr data-series=" not in text
    text = client.get(DATASETS, "admin", view="series").text
    assert text.count("<tr data-series=") == len(CARRIED) and "<tr data-record=" not in text
    assert "Copyrighted: citation required" in text and "Public domain: citation requested" in text
    terms = client.get(DATASETS, "admin", view="terms").text
    assert "not endorsed or certified by the Federal Reserve Bank of St. Louis" in terms
    assert "<om-pager>" in text


def test_the_tools_answer_what_the_pages_show(client: PageClient) -> None:
    assert {t.name for t in pages.tools} == {"read_connection", "read_datasets"}
    connection = client.call_tool("read_connection")
    assert connection.outcome == "unchanged", connection.json
    data = connection.data
    assert data["mode"] == "Sample data" and data["sessions"] is None
    assert data["credentials"] == [{"label": "FRED API key", "set": False}]
    assert data["kept_current"] == 4
    sources = {s["source"]: s for s in data["sources"]}
    assert sources["New York Fed reference rates"]["last_release"] == "2026-10-22"
    assert sources["FOMC target range"]["state"] == "Not read yet"
    read = client.call_tool("read_datasets").data
    assert [s["dataset"] for s in read["served"]] == [
        "fred:fred_public", "fred:fred_cited", "fred:fred_restricted"
    ]  # fmt: skip
    records = {r["name"]: r for r in read["records"]}
    assert records["nyfed:SOFR"]["instrument_id"] == record_id(SOFR)
    assert records["ustreasury:Daily Treasury Par Yield Curve Rates"]["series"][0] == "DGS1MO"
    series = {s["series_id"]: s for s in read["series"]}
    assert series["SOFR"]["dataset"] == CITED and series["DGS10"]["dataset"] == PUBLIC
    assert series["SOFR"]["kept_current"] and not series["DFEDTARL"]["kept_current"]
    assert series["DGS10"]["title"].startswith(
        "Market Yield on U.S. Treasury Securities at 10-Year"
    )
    page = client.get(DATASETS, "admin", view="records").text
    assert all(r["instrument_id"] in page for r in read["records"] if r["instrument_id"])
    assert read["wants"][0]["want_id"] == "w-standing"
    assert read["wants"][0]["state"] == "Kept current"
    lags = {lag["dataset"]: lag for lag in read["lag"]}
    # SOFR for the 22nd, which FRED had at 07:02 Central on the 23rd: 32 h 02 m.
    assert lags[CITED]["rates"] >= 1 and lags[CITED]["longest_seconds"] == 32 * 3600 + 2 * 60


def test_the_series_are_searched(client: PageClient) -> None:
    text = client.get(DATASETS, "admin", q="sofr average").text
    assert 'value="sofr average"' in text
    found = {s.series_id for s in CARRIED if f'data-series="{s.series_id}"' in text}
    assert found == {"SOFR30DAYAVG", "SOFR90DAYAVG", "SOFR180DAYAVG"}
    assert "No series matches" in client.get(DATASETS, "admin", q="drachma").text
    assert len(client.call_tool("read_datasets").data["series"]) == len(CARRIED)


def test_no_key_says_so_and_the_key_is_never_shown(tmp_path: Path) -> None:
    work = feed(tmp_path, lake(), api=LiveApi(""))
    hold(work)
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert "No key" in text and "Enter it in" in text
    keyed = feed(tmp_path, lake(), api=LiveApi(KEY), keyed=True)
    hold(keyed)
    client = PageClient(pages)
    for path in (CONNECTION, DATASETS):
        assert KEY not in client.get(path, "admin").text
    assert client.call_tool("read_connection").data["credentials"] == [
        {"label": "FRED API key", "set": True}
    ]
    assert KEY not in str(client.call_tool("read_connection").json)


def test_before_the_first_check() -> None:
    page_module._held.clear()
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert "No key" in text
    assert "Not resolved yet" in PageClient(pages).get(DATASETS, "admin", view="records").text
    assert "No wants yet" in PageClient(pages).get(DATASETS, "admin").text


def test_fred_not_reached(tmp_path: Path) -> None:
    work = feed(tmp_path, kept=["SOFR"])
    work.status.error = "SOFR: https://api.stlouisfed.org/fred/series?series_id=SOFR: URLError"
    hold(work)
    text = PageClient(pages).get(CONNECTION, "admin").text
    assert 'state="error"' in text and "Not answering" in text and "URLError" in text


def test_a_licensed_dataset_is_said_so(client: PageClient) -> None:
    page_module._held["feed"].wants.licensed = frozenset({PUBLIC})
    served = client.call_tool("read_datasets").data["served"]
    assert [s["licensed"] for s in served] == [True, False, False]


def test_the_figures_are_the_data_roles_in_its_order(client: PageClient) -> None:
    work = page_module._held["feed"]
    said = figures(work.status, work)
    assert [f.label for f in said] == [
        "Connection",
        "Entitled at the vendor",
        "Stream",
        "Last recorded",
    ]
    assert said[0].value == "Sample data" and said[2].value == "Does not stream"
    assert said[1].value == "3 of 3 datasets"
