"""FRED's index series as their publishers' figures (the product owner, items
132 and 136, 2026-11-19; ruling 955): each index's level a `DerivedSeries`
marked `published_by`, never a price, on the index's referential record;
under its copyright class's dataset, a pre-approval series pulled only and
never kept, a cited one kept current; and its publisher's clause recorded
in the dataset's terms."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data.testing import Lake

from fred.declared import CATALOGUE, FRED_CITED, FRED_RESTRICTED, TERMS
from fred.feed import Feed
from fred.series import DJIA_INDEX, NASDAQ_COMPOSITE, SOFR, SP500_INDEX, VIX, carried

from conftest import CITED, RESTRICTED, feed, lake, record_id, want

DERIVED = "meridian.v1.DerivedSeries"


def levels(plugin: Lake) -> list[Any]:
    return [v for params in plugin.on("RecordDerivedSeries") for v in params.values]


def run(work: Feed, *heard: Any) -> None:
    async def go() -> None:
        for each in heard:
            await work.on_observations_wanted(each)

    asyncio.run(go())


def test_an_index_level_is_its_publishers_figure(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin)
    sp500 = record_id(SP500_INDEX)
    run(work, want("w-1", [sp500], day="2026-10-21", dataset=RESTRICTED, data_type=DERIVED))
    [level] = levels(plugin)
    assert [s.entity_id for s in level.meta.subjects] == [sp500]
    assert level.meta.source.dataset == RESTRICTED
    assert level.meta.business_date == "2026-10-21"
    assert level.series == "level"
    assert str(as_decimal(level.value.value)) == "7757.17"
    assert ops.ValueUnit.Name(level.value.unit) == "VALUE_UNIT_INDEX"
    # Whose figure it is, and the publisher's definition; nothing derived.
    assert level.published_by == "S&P Dow Jones Indices LLC"
    assert (level.rule.definition, level.rule.version) == ("S&P 500", 1)
    assert list(level.inputs) == []
    # A pre-approval series is served, never kept: no raw record.
    assert not level.meta.HasField("raw") or not level.meta.raw.key
    assert plugin.on("RecordRates") == [] and plugin.on("DeclineWant") == []


def test_a_pre_approval_index_is_never_pushed(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin, kept=["SP500", "DJIA", "NASDAQCOM"])
    asyncio.run(work.check())
    assert levels(plugin) == [] and plugin.on("RecordRates") == []


def test_a_cited_index_is_kept_current_and_kept(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin, kept=["VIXCLS"])
    asyncio.run(work.check())
    sent = {v.meta.business_date: v for v in levels(plugin)}
    # 12 to 22 October, every business day.
    assert sorted(sent) == [f"2026-10-{d}" for d in (12, 13, 14, 15, 16, 19, 20, 21, 22)]
    vix = sent["2026-10-22"]
    assert vix.meta.source.dataset == CITED
    assert [s.entity_id for s in vix.meta.subjects] == [record_id(VIX)]
    assert str(as_decimal(vix.value.value)) == "19.03"
    assert vix.published_by == "Chicago Board Options Exchange"
    assert vix.meta.raw.key.endswith("-VIXCLS-observations-20261012-20261022.json.gz")
    assert plugin.on("RecordRates") == []


def test_the_nasdaq_composite_states_its_base(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin)
    nasdaq = record_id(NASDAQ_COMPOSITE)
    run(work, want("w-n", [nasdaq], day="2026-10-22", dataset=RESTRICTED, data_type=DERIVED))
    [level] = levels(plugin)
    assert str(as_decimal(level.value.value)) == "26008.860"
    assert level.value.index_base == "1971-02-05=100"
    assert level.published_by == "Nasdaq, Inc."


def test_levels_and_rates_are_asked_apart(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin)
    dow, sofr = record_id(DJIA_INDEX), record_id(SOFR)
    run(
        work,
        # An index's level is no rate.
        want("w-a", [dow], day="2026-10-21", dataset=RESTRICTED),
        # SOFR is no publisher's figure.
        want("w-b", [sofr], day="2026-10-21", dataset=CITED, data_type=DERIVED),
        # A price: neither.
        want("w-c", [dow], day="2026-10-21", dataset=RESTRICTED, data_type="meridian.v1.Price"),
    )
    declined = {d.want_id: ops.UnansweredReason.Name(d.reason) for d in plugin.on("DeclineWant")}
    assert declined == {
        "w-a": "UNANSWERED_REASON_NOT_COVERED",
        "w-b": "UNANSWERED_REASON_NOT_COVERED",
        "w-c": "UNANSWERED_REASON_NOT_COVERED",
    }
    assert levels(plugin) == [] and plugin.on("RecordRates") == []


def test_an_index_not_held_waits_and_is_reported(tmp_path: Path) -> None:
    # The platform seeds no index record yet: a deployment holding none.
    plugin = lake()
    held = plugin.instruments

    def resolve(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        if params.identifiers[0].value == SP500_INDEX.code:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)
        found: ops.ResolveIdentifierResult = held.resolve(params)
        return found

    plugin.answer("ResolveIdentifier", resolve)
    work = feed(tmp_path, plugin)
    run(work, want("w-1", ["INS-SPX"], day="2026-10-21", dataset=RESTRICTED, data_type=DERIVED))
    missing = plugin.on("ReportMissingInstrument")
    assert [(i.scheme, i.value, i.source) for i in missing[0].identifiers] == [
        ("symbol", "SPX", "spdji")
    ]
    assert work.status.subjects[SP500_INDEX.name].miss == "not held"
    assert levels(plugin) == []
    assert [ops.UnansweredReason.Name(d.reason) for d in plugin.on("DeclineWant")] == [
        "UNANSWERED_REASON_NOT_COVERED"
    ]


def test_each_index_is_on_its_referential_record() -> None:
    for series_id, subject in (
        ("SP500", SP500_INDEX),
        ("DJIA", DJIA_INDEX),
        ("NASDAQCOM", NASDAQ_COMPOSITE),
        ("VIXCLS", VIX),
    ):
        held = carried(series_id)
        assert held is not None and held.subject == subject and held.kind == "level"
        assert subject.instrument_type == "index"


def test_every_dataset_serves_publishers_figures_with_their_clauses() -> None:
    for dataset in CATALOGUE:
        assert DERIVED in dataset.data_types
        assert len(dataset.terms_and_pricing) <= 2000
    restricted = TERMS[FRED_RESTRICTED]
    # S&P's and Nasdaq's notices as FRED states them: the publisher's
    # permission needed to reproduce.
    assert (
        "Reproduction of S&P 500 in any form is prohibited except with the prior written "
        "permission of S&P Dow Jones Indices LLC." in restricted
    )
    assert "Dow Jones Industrial Average" in restricted and "NASDAQ OMX Group" in restricted
    cited = TERMS[FRED_CITED]
    assert (
        "Copyright, 2016, Chicago Board Options Exchange, Inc. Reprinted with permission." in cited
    )
