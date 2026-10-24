"""The data suite at contract v27 (meridian.suites), each case FRED's rate
series present mapped to the plugin's own conversion of FRED's recorded
answers: the rates slice's cases as spec/a-public-rates-and-filings-data-
plugin §6 lists them, and the role's cases every data plugin presents.

FRED's rate series are rates, recorded as `Rate` rows (contract v27). The
cases a rates-only plugin never presents -- every case about a price, a
trade, a quote or an outcome, and the feed delay until
core receives ReportLatency (ruling 518) -- are the SDK's
`RATES_NOT_PRESENTED` (ruling 538), each with why. Beside them this plugin
names four of its own: the settlement calendars' two (its datasets declare
no calendar: FRED states none for a series, and it never computes a
settlement date), `two-conventions-one-tenor` (it carries no bill series)
and `records-a-datasets-liveness` (it polls hourly and records no
liveness).

The cases every suite holds that the SDK answers (a replacement, the
template catalogue, an event group heard) are the SDK's.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles.data.testing import RATES_NOT_PRESENTED, Instruments
from meridian.suites import ANSWERED_BY_SDK, Recorder, run

from fred.feed import NEW_YORK
from fred.series import PAR, SOFR

from conftest import CITED, PUBLIC, Revised, feed, record_id, seeded, want

NOT_PRESENTED = {
    **RATES_NOT_PRESENTED,
    "reads-a-calendar": "its datasets declare no calendar: FRED states none for a series",
    "asks-for-a-settlement-date": (
        "records each rate as published; never computes a settlement date"
    ),
    "two-conventions-one-tenor": (
        "it carries no bill series, so no discount rate and coupon-equivalent yield"
    ),
    "records-a-datasets-liveness": (
        "it polls FRED hourly and records no liveness: each series changes once a day at most"
    ),
}


def _seeded(recorder: Recorder, ambiguous: bool = False) -> None:
    if ambiguous:
        recorder.answer(
            "ResolveIdentifier",
            lambda _: ops.ResolveIdentifierResult(
                found=False, miss_reason=ops.MISS_REASON_AMBIGUOUS
            ),
        )
        return
    seeded(Instruments().answering(recorder))


def producers(tmp: Path) -> dict[str, Callable[[Recorder], Awaitable[None]]]:
    def kept(*series: str) -> Callable[[Recorder], Awaitable[None]]:
        async def produce(recorder: Recorder) -> None:
            _seeded(recorder)
            await feed(tmp, recorder, kept=series).check()

        return produce

    async def two_records(recorder: Recorder) -> None:
        # SOFR's code meets two of the deployment's records.
        _seeded(recorder, ambiguous=True)
        await feed(tmp, recorder, kept=["SOFR"]).check()

    async def revised(recorder: Recorder) -> None:
        # The 22nd's SOFR wanted, then FRED revises it, and it is wanted
        # again: the same row key, a new value, a later published time.
        _seeded(recorder)
        api = Revised()
        work = feed(tmp, recorder, api=api)
        sofr = record_id(SOFR)
        for n in (1, 2):
            asked = want(f"w-{n}", [sofr], day="2026-10-22", dataset=CITED).message
            recorder.answer("ObservationsWanted", lambda _, held=asked: held)  # type: ignore[misc]
            await recorder.receive(observations_wanted=work.on_want)
            api.revised = True

    def the_curve(*days: str) -> Callable[[Recorder], Awaitable[None]]:
        # Treasury's nominal curve from H.15's series around the 1-month's
        # first day, 31 July 2001: on the 30th no 1-month point, on the 31st
        # one.
        async def produce(recorder: Recorder) -> None:
            _seeded(recorder)
            work = feed(tmp, recorder)
            message = want(
                "w-curve", [record_id(PAR)], day=days[0] if len(days) == 1 else ""
            ).message
            if len(days) > 1:
                start = datetime.fromisoformat(days[0]).replace(tzinfo=NEW_YORK)
                end = datetime.fromisoformat(days[-1]).replace(tzinfo=NEW_YORK) + timedelta(days=1)
                message.valid_from_ns = int(start.timestamp()) * 10**9
                message.valid_until_ns = int(end.timestamp()) * 10**9
            recorder.answer("ObservationsWanted", lambda _: message)
            await recorder.receive(observations_wanted=work.on_want)
            sent = [r for b in recorder.on("RecordRates") for r in b.rates]
            on_30th = {
                (r.tenor.count, r.tenor.unit) for r in sent if r.meta.business_date == "2001-07-30"
            }
            assert sent and (1, ops.TENOR_UNIT_MONTH) not in on_30th, "no 1-month point, no zero"

        return produce

    async def licences(recorder: Recorder) -> None:
        recorder.answer(
            "ListDatasets",
            lambda _: ops.ListDatasetsResult(licences=[ops.DatasetLicence(dataset=PUBLIC)]),
        )
        work = feed(tmp, recorder)
        await work.wants.read_licences()
        assert work.wants.licensed == {PUBLIC}

    async def declined(recorder: Recorder) -> None:
        _seeded(recorder)
        work = feed(tmp, recorder)
        asked = want("w-2", ["INS-NOT-CARRIED"], day="2026-10-21").message
        recorder.answer("ObservationsWanted", lambda _: asked)
        await recorder.receive(observations_wanted=work.on_want)

    async def withdrawn(recorder: Recorder) -> None:
        _seeded(recorder)
        work = feed(tmp, recorder)
        recorder.answer(
            "WantWithdrawn",
            lambda _: ops.WantWithdrawnEvent(want_id="w-standing", dataset=PUBLIC),
        )
        await recorder.receive(want_withdrawn=work.on_withdrawn)

    return {
        "an-asset-that-does-not-resolve": two_records,
        "a-subject-declined": declined,
        "a-standing-want-withdrawn": withdrawn,
        "reads-its-datasets-licences": licences,
        "a-rate-fixing": kept("SOFR"),
        "a-same-day-revision": revised,
        "a-curve-for-a-date": the_curve("2001-07-30", "2001-07-31"),
        "a-tenor-not-published": the_curve("2001-07-30"),
        "an-index-level": kept("SOFRINDEX"),
        "a-curve-point-from-another-source": kept("DGS10"),
    }


def test_the_data_suite_passes(tmp_path: Path) -> None:
    report = run("data", producers(tmp_path), not_presented=NOT_PRESENTED, instance_id="fred")
    assert report.passed, report.failures
    assert sorted(report.not_presented) == sorted(NOT_PRESENTED)
    # The plugin's own ten, and the cases every suite holds that the SDK answers.
    assert len(report.passed_cases) == 10 + len(ANSWERED_BY_SDK)
    assert report.answered_by_sdk == list(ANSWERED_BY_SDK)
