"""The pages on sample data, each printed as one HTML file: for looking at
them without a deployment.

    python -m fred.preview connection > preview/connection.html
    python -m fred.preview datasets > preview/datasets.html

The plugin's work runs on the SDK's suite recorder in place of a sidecar --
every seeded referential record held, every batch recorded -- against the
answers committed under responses/, at 14:00 UTC on 23 October 2026: SOFR,
EFFR, the SOFR Index and Treasury's nominal curve kept current and read, a
want for SOFR on 24 September answered, one for Columbus Day declined (FRED
states nothing), and a standing want for €STR kept current. Each page links
the kit where the dashboard serves it, /.meridian/ui/<version>/: served
beside the kit it is styled (`make preview SHOTS=...`, which checks each in a
browser); opened on its own it is the page without the kit, unstyled, which
works too. `connection-first` and `datasets-first` are the pages with no key
and before the first check: the role's "not set up yet" states.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

from meridian.plugin.v1 import operations_pb2 as ops
from meridian.receive import Heard
from meridian.roles.data.testing import Instruments
from meridian.suites import Recorder
from meridian.testing import PageClient

from .api import LiveApi, SyntheticApi
from .feed import Feed
from .page import CONNECTION, DATASETS, hold, pages
from .raw import RawStore
from .series import CARRIED, ESTR, PAR, SOFR, SUBJECTS, Subject

AT = datetime(2026, 10, 23, 14, 0, tzinfo=UTC)
PAGES = {
    "connection": CONNECTION,
    "datasets": DATASETS,
    "datasets-search": DATASETS,
    "datasets-series": DATASETS,
    "datasets-terms": DATASETS,
    "connection-first": CONNECTION,
    "datasets-first": DATASETS,
}
#: What the Datasets tab's search is shown with, as `datasets-search`.
SEARCHED = "sofr"
KEPT = ["SOFR", "EFFR", "SOFRINDEX"] + [s.series_id for s in CARRIED if s.subject == PAR]


def _id(subject: Subject) -> str:
    return "INS-" + "".join(c for c in subject.code if c.isalnum())[:20]


def _want(
    want_id: str, subject: Subject, day: str = "", dataset: str = "fred:fred_cited",
    standing: bool = False,
) -> Heard:  # type: ignore[type-arg]  # fmt: skip
    return Heard(
        row="ObservationsWanted",
        message=ops.ObservationsWantedEvent(
            want_id=want_id,
            dataset=dataset,
            data_type="meridian.v1.Rate",
            subjects=[ops.SubjectRef(entity_id=_id(subject))],
            business_date=day,
            standing=standing,
        ),
    )


def _recorder() -> Recorder:
    recorder = Recorder("fred")
    store = Instruments().answering(recorder)
    for subject in SUBJECTS:
        store.hold(
            _id(subject),
            ops.Identifier(scheme="symbol", value=subject.code, source=subject.source),
        )
    return recorder


async def synthetic_feed() -> Feed:
    """A feed as sample data leaves it, on the recorder."""
    feed = Feed(_recorder(), SyntheticApi(lambda: AT), RawStore(), now=lambda: AT, kept=KEPT)
    await feed.check()
    await feed.on_want(_want("want-0924", SOFR, "2026-09-24"))
    await feed.on_want(_want("want-1012", SOFR, "2026-10-12"))
    await feed.on_want(_want("want-standing", ESTR, dataset="fred:fred_public", standing=True))
    return feed


def render(page: str) -> str:
    if page.endswith("-first"):
        feed = Feed(_recorder(), LiveApi(""), RawStore(), now=lambda: AT)
    else:
        feed = asyncio.run(synthetic_feed())
    hold(feed)
    query = {"q": SEARCHED} if page == "datasets-search" else {}
    if page in ("datasets-series", "datasets-terms"):
        query = {"view": page.removeprefix("datasets-")}
    answer = PageClient(pages).get(PAGES[page], "admin", **query)
    if answer.status != 200:
        raise SystemExit(f"{page} answered {answer.status}: {answer.text[:200]}")
    return answer.text


def main() -> None:
    page = sys.argv[1] if len(sys.argv) > 1 else "connection"
    if page not in PAGES:
        raise SystemExit(f"no page {page!r}: {', '.join(PAGES)}")
    sys.stdout.write(render(page))


if __name__ == "__main__":
    main()
