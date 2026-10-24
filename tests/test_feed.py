"""FRED's rate series into the lake: the series kept current, rates exact,
revisions as next versions, restarts unchanged, classes as datasets, and
the lake's wants answered or declined, each with why."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from meridian.operations import as_decimal
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data.testing import Lake

from fred.api import TAGS, Fetched, SyntheticApi
from fred.feed import Feed, number, updated_ns
from fred.raw import RawStore
from fred.series import CARRIED, ESTR, PAR, SOFR, SOFR_INDEX

from conftest import AT, CITED, PUBLIC, RESTRICTED, Revised, feed, lake, record_id, want


def rows(plugin: Lake) -> list[Any]:
    return plugin.rows("RecordRates")


def run(work: Feed, *heard: Any) -> None:
    async def go() -> None:
        for each in heard:
            await work.on_want(each)

    asyncio.run(go())


def test_sofr_is_a_fixing_with_its_percentiles_volume_and_convention(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin, kept=["SOFR"])
    done = asyncio.run(work.check())
    sent = {r.meta.business_date: r for r in rows(plugin)}
    # 12 to 22 October, but Columbus Day, the 12th, which FRED states as ".".
    assert done.recorded == len(sent) == 8 and "2026-10-12" not in sent
    sofr = sent["2026-10-22"]
    assert sofr.meta.source.dataset == CITED
    assert [s.entity_id for s in sofr.meta.subjects] == [record_id(SOFR)]
    assert ops.RateKind.Name(sofr.kind) == "RATE_KIND_FIXING"
    assert str(as_decimal(sofr.value.value)) == "3.90"
    assert ops.ValueUnit.Name(sofr.value.unit) == "VALUE_UNIT_PERCENT"
    assert ops.DayCount.Name(sofr.convention.day_count) == "DAY_COUNT_ACT_360"
    assert {p.percentile: str(as_decimal(p.value)) for p in sofr.percentiles} == {
        1: "3.83", 25: "3.88", 75: "3.95", 99: "3.98"
    }  # fmt: skip
    # SOFRVOL states billions of dollars.
    assert as_decimal(sofr.volume.amount) == Decimal("2945e9")
    assert sofr.volume.currency_code == "USD"
    assert sofr.meta.business_date == "2026-10-22"
    assert sofr.meta.raw.key.endswith("-SOFR-observations-20261012-20261022.json.gz")


def test_a_rate_is_exact_never_a_float(tmp_path: Path) -> None:
    plugin = lake()
    asyncio.run(feed(tmp_path, plugin, kept=["SOFRINDEX", "ECBESTRVOLWGTTRMDMNRT"]).check())
    index = [r for r in rows(plugin) if r.meta.subjects[0].entity_id == record_id(SOFR_INDEX)]
    latest = max(index, key=lambda r: r.meta.business_date)
    assert str(as_decimal(latest.value.value)) == "1.26384966"
    assert ops.ValueUnit.Name(latest.value.unit) == "VALUE_UNIT_INDEX"
    assert latest.value.index_base == "2018-04-02=1.00000000"
    estr = [r for r in rows(plugin) if r.meta.subjects[0].entity_id == record_id(ESTR)]
    assert {str(as_decimal(r.value.value)) for r in estr} >= {"2.442", "2.440"}
    assert estr[0].meta.source.dataset == PUBLIC
    # ECBESTRTOTVOL states millions of euros.
    assert all(r.volume.currency_code == "EUR" for r in estr)
    assert number(".") is None and number("NaN") is None and number("3.90") == Decimal("3.90")


def test_every_rate_states_its_convention(tmp_path: Path) -> None:
    # The lake keeps no rate without one, an index level among them.
    plugin = lake()
    asyncio.run(feed(tmp_path, plugin, kept=[s.series_id for s in CARRIED]).check())
    assert rows(plugin) and all(r.HasField("convention") for r in rows(plugin))


def test_only_the_latest_observation_has_a_published_time(tmp_path: Path) -> None:
    plugin = lake()
    asyncio.run(feed(tmp_path, plugin, kept=["SOFR"]).check())
    published = {r.meta.business_date: list(r.meta.source_times) for r in rows(plugin)}
    assert [t.at_ns for t in published["2026-10-22"]] == [updated_ns("2026-10-23 07:02:00-05")]
    assert all(not times for day, times in published.items() if day != "2026-10-22")


def test_a_curves_points_are_rows_against_one_record(tmp_path: Path) -> None:
    plugin = lake()
    nominal = [s.series_id for s in CARRIED if s.subject == PAR]
    asyncio.run(feed(tmp_path, plugin, kept=nominal).check())
    day = [r for r in rows(plugin) if r.meta.business_date == "2026-10-21"]
    assert {r.meta.subjects[0].entity_id for r in day} == {record_id(PAR)}
    labels = sorted((r.tenor.unit, r.tenor.count) for r in day)
    assert len(labels) == 11 and all(r.kind == ops.RATE_KIND_PAR_YIELD for r in day)
    ten = next(r for r in day if r.tenor.count == 10 and r.tenor.unit == ops.TENOR_UNIT_YEAR)
    assert str(as_decimal(ten.value.value)) == "5.13"
    assert ten.convention.periods_per_year == 2
    assert ten.meta.row_key.startswith("fred:par_yield:10Y:act_act:compounded/2:2026-10-21@")


def test_an_hour_with_nothing_new_reads_metadata_only(tmp_path: Path) -> None:
    api = SyntheticApi(lambda: AT)
    work = feed(tmp_path, kept=["SOFR"], api=api)
    asyncio.run(work.check())
    asked = len(api.asked)
    again = asyncio.run(work.check())
    assert again.recorded == again.unchanged == 0
    assert api.asked[asked:] == ["/fred/series?series_id=SOFR&file_type=json"]


def test_a_restart_records_nothing_twice(tmp_path: Path) -> None:
    plugin = lake()
    asyncio.run(feed(tmp_path, plugin, kept=["SOFR"]).check())
    first = rows(plugin)
    later = feed(tmp_path, plugin, kept=["SOFR"])
    done = asyncio.run(later.check())
    assert done.recorded == done.restated == 0 and done.unchanged == 8
    second = rows(plugin)[len(first) :]
    # The same raw record and published time as first read, so the lake's
    # whole comparison finds nothing new.
    assert [(r.meta.raw.key, list(r.meta.source_times)) for r in second] == [
        (r.meta.raw.key, list(r.meta.source_times)) for r in first
    ]


def test_a_same_day_revision_is_the_next_version(tmp_path: Path) -> None:
    plugin = lake()
    api = Revised()
    work = feed(tmp_path, plugin, kept=["SOFR"], api=api)
    asyncio.run(work.check())
    api.revised = True
    done = asyncio.run(work.check())
    assert done.restated == 1 and done.unchanged == 7
    revised = rows(plugin)[-1]
    assert revised.meta.business_date == "2026-10-22"
    assert str(as_decimal(revised.value.value)) == "3.91"
    assert [t.at_ns for t in revised.meta.source_times] == [updated_ns("2026-10-23 09:30:00-05")]
    original = next(r for r in rows(plugin) if r.meta.business_date == "2026-10-22")
    assert original.meta.row_key == revised.meta.row_key


def test_a_want_is_recorded_against(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin)
    run(work, want("w-1", [record_id(SOFR)], day="2026-09-24", dataset=CITED))
    sent = plugin.on("RecordRates")
    assert [b.want_id for b in sent] == ["w-1"]
    assert [r.meta.business_date for r in sent[0].rates] == ["2026-09-24"]
    assert [str(as_decimal(r.value.value)) for r in sent[0].rates] == ["3.88"]
    assert plugin.on("DeclineWant") == []


def test_wants_declined_with_why(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin)
    sofr = record_id(SOFR)
    run(
        work,
        # A subject it carries no series of.
        want("w-a", ["INS-ELSEWHERE"], day="2026-10-21"),
        # SOFR is cited, so not served under fred_public.
        want("w-b", [sofr], day="2026-10-21", dataset=PUBLIC),
        # Columbus Day: FRED states nothing.
        want("w-c", [sofr], day="2026-10-12", dataset=CITED),
        # Before SOFR's first observation, 3 April 2018.
        want("w-d", [sofr], day="2017-06-01", dataset=CITED),
        # A price: it records rates.
        want("w-e", [sofr], day="2026-10-21", dataset=CITED, data_type="meridian.v1.Price"),
    )
    declined = {d.want_id: ops.UnansweredReason.Name(d.reason) for d in plugin.on("DeclineWant")}
    assert declined == {
        "w-a": "UNANSWERED_REASON_NOT_COVERED",
        "w-b": "UNANSWERED_REASON_NOT_COVERED",
        "w-c": "UNANSWERED_REASON_SOURCE_SILENT",
        "w-d": "UNANSWERED_REASON_BEYOND_HISTORY",
        "w-e": "UNANSWERED_REASON_NOT_COVERED",
    }
    assert plugin.on("RecordRates") == []


def test_without_a_key_nothing_is_asked(tmp_path: Path) -> None:
    from fred.api import LiveApi

    plugin = lake()
    api = LiveApi("")
    work = feed(tmp_path, plugin, kept=["SOFR"], api=api)
    asyncio.run(work.check())
    run(work, want("w-1", [record_id(SOFR)], day="2026-10-21", dataset=CITED))
    assert plugin.on("RecordRates") == [] and work.status.fetches == 0
    declined = plugin.on("DeclineWant")
    assert [ops.UnansweredReason.Name(d.reason) for d in declined] == [
        "UNANSWERED_REASON_NOT_ENTITLED"
    ]


def test_a_standing_want_is_kept_current_until_withdrawn(tmp_path: Path) -> None:
    from meridian.receive import Heard

    plugin = lake()
    work = feed(tmp_path, plugin)
    run(work, want("w-s", [record_id(ESTR)], standing=True))
    assert [s.series_id for s in work.current_series()] == ["ECBESTRVOLWGTTRMDMNRT"]
    assert plugin.on("RecordRates")[0].want_id == "w-s"

    async def withdraw() -> None:
        await work.on_withdrawn(
            Heard(row="WantWithdrawn", message=ops.WantWithdrawnEvent(want_id="w-s"))
        )

    asyncio.run(withdraw())
    assert work.current_series() == []


def test_a_record_not_held_is_reported_and_its_rates_wait(tmp_path: Path) -> None:
    plugin = lake()
    held = plugin.instruments

    def resolve(params: ops.ResolveIdentifierParams) -> ops.ResolveIdentifierResult:
        if params.identifiers[0].value == SOFR.code:
            return ops.ResolveIdentifierResult(found=False, miss_reason=ops.MISS_REASON_NOT_FOUND)
        found: ops.ResolveIdentifierResult = held.resolve(params)
        return found

    plugin.answer("ResolveIdentifier", resolve)
    work = feed(tmp_path, plugin, kept=["SOFR", "EFFR"])
    asyncio.run(work.check())
    assert {r.meta.subjects[0].entity_id for r in rows(plugin)} == {"INS-EFFR"}
    missing = plugin.on("ReportMissingInstrument")
    assert [(i.scheme, i.value, i.source) for i in missing[0].identifiers] == [
        ("symbol", "SOFR", "nyfed")
    ]
    assert work.status.subjects["nyfed:SOFR"].miss == "not held"


class Reclassed(SyntheticApi):
    """FRED, SOFR's class changed to pre-approval required."""

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        if path.startswith(TAGS) and "series_id=SOFR&" in path:
            answer = json.loads(got.body)
            for tag in answer["tags"]:
                if tag["group_id"] == "cc":
                    tag["name"] = "copyrighted: pre-approval required"
            return Fetched(path, 200, json.dumps(answer).encode(), got.fetched_at)
        return got


def test_a_series_whose_class_changes_moves_dataset(tmp_path: Path) -> None:
    plugin = lake()
    work = feed(tmp_path, plugin, kept=["SOFR"])
    asyncio.run(work.check())
    assert {r.meta.source.dataset for r in rows(plugin)} == {CITED}
    count = len(rows(plugin))
    work.api = Reclassed(lambda: AT)
    work.status.series["SOFR"].classed_on = None
    asyncio.run(work.check())
    # Restricted: pulled only, so no longer pushed; the change is kept.
    assert len(rows(plugin)) == count
    held = work.status.series["SOFR"]
    assert held.copyright_class == "restricted"
    assert [(was, now) for _, was, now in held.changes] == [("cited", "restricted")]
    # Wanted, it is served under fred_restricted, its answer not kept.
    kept_before = len(work.raw.keys())
    run(work, want("w-r", [record_id(SOFR)], day="2026-10-21", dataset=RESTRICTED))
    served = plugin.on("RecordRates")[-1]
    assert served.want_id == "w-r" and served.rates[0].meta.source.dataset == RESTRICTED
    assert not served.rates[0].meta.HasField("raw")
    assert all("-observations-" not in k for k in work.raw.keys()[kept_before:])


def test_its_rows_never_name_a_raw_record_outside_storage(tmp_path: Path) -> None:
    plugin = lake()
    asyncio.run(feed(tmp_path, plugin, kept=["DGS10"]).check())
    store = RawStore(tmp_path)
    for row in rows(plugin):
        kept = store.read(row.meta.raw.key)
        assert kept is not None and kept["status"] == 200
        assert "api_key" not in kept["url"]
