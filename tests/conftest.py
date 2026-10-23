"""Shared stand-ins: FRED's recorded answers, a fixed clock, the deployment's
seeded referential records, and the lake's wants as the sidecar delivers
them."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data.testing import Instruments, Lake
from meridian.suites import Recorder

from fred.api import OBSERVATIONS, Fetched, SyntheticApi
from fred.feed import Feed
from fred.raw import RawStore
from fred.series import SUBJECTS, Subject

#: After the recording: 14:00 UTC on Friday 23 October 2026, 10:00 in New
#: York, the 22nd's New York Fed rates published at 07:02 Central.
AT = datetime(2026, 10, 23, 14, 0, tzinfo=UTC)
INSTANCE = "fred"
PUBLIC = f"{INSTANCE}:fred_public"
CITED = f"{INSTANCE}:fred_cited"
RESTRICTED = f"{INSTANCE}:fred_restricted"
RATE = "meridian.v1.Rate"


def record_id(subject: Subject) -> str:
    """The `INS-` ID the tests hold a seeded record under."""
    return "INS-" + "".join(c for c in subject.code if c.isalnum())[:20]


def seeded(store: Instruments, *left_out: Subject) -> Instruments:
    """The deployment holding the platform's seeded referential records,
    each by its administrator's code as a source-scoped symbol, but
    `left_out`."""
    for subject in SUBJECTS:
        if subject in left_out:
            continue
        store.hold(
            record_id(subject),
            ops.Identifier(scheme="symbol", value=subject.code, source=subject.source),
        )
    return store


def lake(*left_out: Subject) -> Lake:
    """The lake as a test stands it in, holding the seeded records."""
    held = Lake(INSTANCE)
    seeded(held.instruments, *left_out)
    return held


def feed(
    tmp: Path,
    plugin: Recorder | None = None,
    *,
    kept: Sequence[str] = (),
    api: Any = None,
    at: datetime = AT,
    keyed: bool = False,
) -> Feed:
    """The plugin's work on the lake and FRED's recorded answers, at `at`."""
    return Feed(
        plugin if plugin is not None else lake(),
        api or SyntheticApi(lambda: at),
        RawStore(tmp),
        now=lambda: at,
        kept=kept,
        keyed=keyed,
    )


class Revised(SyntheticApi):
    """FRED, its SOFR for 22 October revised from 3.90 to 3.91 after
    `revised` is set, under a later `last_updated`, as a fixing the New York
    Fed corrects the same day shows on FRED."""

    def __init__(self) -> None:
        super().__init__(lambda: AT)
        self.revised = False

    async def get(self, path: str) -> Fetched:
        got = await super().get(path)
        if not self.revised or "series_id=SOFR&" not in path:
            return got
        answer = json.loads(got.body)
        if path.startswith(OBSERVATIONS):
            for observation in answer["observations"]:
                if observation["date"] == "2026-10-22":
                    observation["value"] = "3.91"
        elif "seriess" in answer:
            answer["seriess"][0]["last_updated"] = "2026-10-23 09:30:00-05"
        return Fetched(path, 200, json.dumps(answer).encode(), got.fetched_at)


def want(
    want_id: str,
    subjects: list[str],
    *,
    day: str = "",
    standing: bool = False,
    dataset: str = PUBLIC,
    data_type: str = RATE,
    valid_from_ns: int = 0,
    valid_until_ns: int = 0,
) -> Heard:  # type: ignore[type-arg]
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=dataset,
            data_type=data_type,
            subjects=[ops.SubjectRef(entity_id=s) for s in subjects],
            business_date=day,
            standing=standing,
            valid_from_ns=valid_from_ns,
            valid_until_ns=valid_until_ns,
        ),
    )
