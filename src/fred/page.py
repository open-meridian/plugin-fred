"""The plugin's pages, under Manage alone: the data role's common pages
(spec/plugin-pages-follow-their-role), Connection and Datasets, in its
order, each also a read tool for agents on the deployment's MCP under the
role's names (`read_connection`, `read_datasets`). Each record is the
role's (`meridian.roles.data`), extended with FRED's fields; each template
is the role's, with FRED's nuance at its blocks only.

A data plugin shows its connectivity, its data subscriptions and how its
entitlements resolve, and no market data (the product owner, 2026-10-03).
So, as spec/a-public-rates-and-filings-data-plugin §5 has them:

- **Connection** (`/`): "Key" -- the mode (Live, Sample data or No key),
  whether FRED's API key is set (never its value), what FRED serves, and
  **Sources**, a row whose detail is one line per publisher's rates FRED
  carries (its state, the latest day stated, its calls, its last error; the
  next expected is not known, since no calendar is declared) and how many
  series are kept current; "Limits and use" -- FRED's 120 requests a minute,
  the requests made, the last call and error; "Stream": it does not stream.
  The role draws "Sessions" once a session is measured: FRED is polled, so
  never.
- **Datasets** (`/datasets`): the role's sections and FRED's as tabs, one
  shown at a time (`?view=`) so the page fits one screen: "Served" (with
  **Lag** as a column, the median published-minus-valid time) and
  "Subjects" under it, "Wants", **Records** (each rate and curve and its
  `INS-`, or why none), **FRED series** (each series' copyright class,
  dataset and class changes, searched) and **Terms** (the notice and
  citation FRED's terms ask for) -- one line a row, paged by the kit's
  om-pager.

Neither shows a rate: rates are the reading roles' to show. Settings change
through core's tools; the pages hold no actions.
"""

from __future__ import annotations

import statistics
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import meridian
from meridian.roles import data

from . import records
from .api import BASE, SPACING
from .classes import SAID, dataset_of
from .declared import CATALOGUE
from .feed import Feed, Status
from .series import CARRIED, SUBJECTS, Series, of_subject

TITLE = "FRED"
#: The kit these pages are built on: the dev deployment's, from v27.
KIT = "0.13.0"

pages = meridian.Pages(TITLE, templates=Path(__file__).parent / "templates", kit=KIT)

CONNECTION = "/"
DATASETS = "/datasets"

#: The longest search the Datasets tab reads.
MOST_QUERY = 100
#: The Datasets page's tabs, one shown at a time (`?view=`), the first by default.
VIEWS = ("served", "wants", "records", "series", "terms")
#: How many wants the Datasets tab lists; read_datasets answers every one held.
SHOWN_WANTS = 3
#: What FRED's terms ask be said, and each class's citation (§7), on the
#: Terms tab: the licence's attribution fields are held until core v27
#: accepts them at registration (declared.py).
ATTRIBUTION = (
    "This product uses the FRED® API but is not endorsed or certified by the Federal "
    "Reserve Bank of St. Louis. Cite each series' source as FRED's suggested citation "
    "gives it: <publisher>, <title> [<ID>], retrieved from FRED, Federal Reserve Bank of "
    "St. Louis. A copyrighted series is its publisher's: citation is required, and a "
    "pre-approval series is reproduced only with its owner's permission."
)
#: Each source, by its subjects' administrator, as "Sources" names it.
SOURCES = {
    "nyfed": "New York Fed reference rates",
    "frb": "FOMC target range",
    "ecb": "Euro short-term rate (€STR)",
    "ustreasury": "Treasury par yield curves (H.15)",
}

_held: dict[str, Feed] = {}


def hold(feed: Feed) -> None:
    """The feed the pages read, once the plugin has registered."""
    _held["feed"] = feed


def _status() -> tuple[Status, Feed | None]:
    feed = _held.get("feed")
    return (feed.status if feed is not None else Status(), feed)


def _iso(moment: datetime | None) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds") if moment else ""


def _day(day: date | None) -> str:
    return day.isoformat() if day else ""


def _mode(status: Status) -> str:
    if status.mode == "synthetic":
        return "Sample data"
    return "Live" if status.keyed else "No key"


def _state(status: Status, feed: Feed | None) -> tuple[str, str, str]:
    """The head's status: its state, what it means, and its detail."""
    mode = _mode(status)
    if mode == "No key":
        return "warn", "No key", "Enter FRED's API key in Settings"
    misses = sorted(s.subject.name for s in status.subjects.values() if s.miss)
    if status.error and status.read_at is None:
        return "error", "Not answering", status.error
    if status.error:
        return "warn", "Answering", status.error
    if feed is not None and not feed.current_series():
        return "ok", "Nothing kept current", "Series are fetched when wanted"
    if status.read_at is None:
        return "busy", "Checking FRED", ""
    if misses:
        plural = "record" if len(misses) == 1 else "records"
        return "warn", f"{len(misses)} {plural} not held", ", ".join(misses)
    return "ok", "Sample data" if mode == "Sample data" else "Answering", ""


def _sources(status: Status, feed: Feed | None) -> list[records.SourceRead]:
    held = []
    for source, name in SOURCES.items():
        mine = [s for s in CARRIED if s.subject.source == source]
        ids = {s.series_id for s in mine} | {c for s in mine for c in s.companions}
        seen = [status.series[i] for i in ids if i in status.series]
        latest = max((s.latest_day for s in seen if s.latest_day), default=None)
        errors = [s.error for s in seen if s.error]
        held.append(
            records.SourceRead(
                source=name,
                publisher=mine[0].publisher,
                series=len(mine),
                state="Not read yet" if not seen else ("Failing" if errors else "Answering"),
                last_release=_day(latest),
                next_expected="",
                calls=sum(s.calls for s in seen),
                last_error=errors[0] if errors else "",
            )
        )
    return held


def connection_read(status: Status, feed: Feed | None) -> records.ConnectionRead:
    state, said, _ = _state(status, feed)
    kept = feed.raw.keys() if feed is not None else []
    window = ""
    if feed is not None and feed.raw.granted:
        window = "in the storage the deployment grants, as its responses settings say"
    elif feed is not None:
        window = "in a directory of the plugin's own: this deployment grants no storage"
    mode = _mode(status)
    return records.ConnectionRead(
        mode=mode,
        credentials=[data.Credential("FRED API key", status.keyed)],
        entitled_at_vendor=(
            "" if mode == "No key" else f"Every series FRED publishes; {len(CARRIED)} carried"
        ),
        limit=(
            f"FRED's 120 requests a minute for a key; the plugin asks one at a time, at most "
            f"one every {SPACING:g} s, and checks the series kept current every hour"
        ),
        calls=status.fetches,
        rate_limited=feed.api.rate_limited if feed is not None else 0,
        last_call_at=_iso(status.checked_at),
        last_error=status.error,
        sessions=None,
        state=state,
        said=said,
        source=(
            "The answers recorded on 23 October 2026, committed with the plugin"
            if status.mode == "synthetic"
            else f"{BASE}/fred, the series this plugin carries"
        ),
        checked_at=_iso(status.checked_at),
        kept_current=len(feed.current_series()) if feed is not None else 0,
        sources=_sources(status, feed),
        responses_kept=len(kept),
        kept_for=window,
    )


def _duration(seconds: int) -> str:
    hours, rest = divmod(max(seconds, 0), 3600)
    return f"{hours} h {rest // 60:02d} m"


def lag_read(status: Status, dataset: str, key: str) -> records.LagRead:
    lags = status.lags.get(key, [])
    if not lags:
        return records.LagRead(dataset=dataset, said="No rate read with its published time yet")
    median, longest = int(statistics.median(lags)), max(lags)
    return records.LagRead(
        dataset=dataset,
        rates=len(lags),
        median_seconds=median,
        longest_seconds=longest,
        median=f"{_duration(median)} median",
        said=f"{_duration(median)} median, {_duration(longest)} longest, of {len(lags)} rates",
    )


def _series_read(status: Status, feed: Feed | None, series: Series) -> records.SeriesRead:
    held = status.series.get(series.series_id)
    instance = feed.plugin.identity.instance_id if feed is not None else "fred"
    kept = feed is not None and series in feed.current_series()
    if held is None:
        return records.SeriesRead(
            series_id=series.series_id, of=f"{series.subject.name}, {series.point}",
            kept_current=kept,
        )  # fmt: skip
    key = dataset_of(held.copyright_class)
    return records.SeriesRead(
        series_id=series.series_id,
        of=f"{series.subject.name}, {series.point}",
        title=held.title,
        copyright_class=SAID.get(held.copyright_class, ""),
        dataset=f"{instance}:{key}" if key else "",
        changes=[
            f"{at}: {SAID.get(was, was)} to {SAID.get(now, now)}" for at, was, now in held.changes
        ],
        kept_current=kept,
        first_day=held.first_day,
        latest_day=_day(held.latest_day),
        last_updated=held.last_updated,
        last_error=held.error,
    )


def datasets_read(status: Status, feed: Feed | None) -> records.DatasetsRead:
    instance = feed.plugin.identity.instance_id if feed is not None else "fred"
    mode = _mode(status)
    entitled = "No: no key set" if mode == "No key" else "Yes: every series FRED publishes"
    served = data.served(CATALOGUE, instance, feed.wants if feed is not None else None, entitled)
    terms = {
        "fred_public": "kept, derived use, display; FRED's notice",
        "fred_cited": "kept, derived use, display; cite the source",
        "fred_restricted": "served, not kept; no derived use; display",
    }
    served = [replace(s, default_terms=terms[s.dataset.partition(":")[2]]) for s in served]
    return records.DatasetsRead(
        served=served,
        wants=list(data.want_rows(feed.wants)) if feed is not None else [],
        reads_instruments=True,
        attribution=ATTRIBUTION,
        records=[
            records.RecordRead(
                name=subject.name,
                description=subject.description,
                instrument_type=subject.instrument_type.replace("_", " "),
                series=[s.series_id for s in of_subject(subject)],
                instrument_id=held.instrument_id if held else "",
                miss=held.miss if held else "",
            )
            for subject in SUBJECTS
            for held in [status.subjects.get(subject.name)]
        ],
        series=[_series_read(status, feed, s) for s in CARRIED],
        lag=[lag_read(status, f"{instance}:{d.key}", d.key) for d in CATALOGUE],
        unread=[f"{line} ({n} reads)" for line, n in sorted(status.unread.items())],
    )


def figures(status: Status, feed: Feed | None) -> list[meridian.Figure]:
    """The data role's figures, in its order (`meridian.roles.data`); FRED's
    plugin reports none of its own."""
    state, said, why = _state(status, feed)
    if status.mode == "synthetic" and state == "ok":
        connection: Any = "Sample data"
    elif said in ("Not answering", "No key"):
        connection = meridian.Figure("", said, state="error" if state == "error" else "warn",
                                     why=why[:200])  # fmt: skip
    else:
        connection = meridian.Figure(
            "", "Answering", state="warn" if status.error else None, why=status.error[:200]
        )
    last = feed.wants.counts.last_ns if feed is not None else 0
    entitled = "0 of 3 datasets: no key" if _mode(status) == "No key" else "3 of 3 datasets"
    return data.figures(
        connection=connection,
        entitled_at_vendor=entitled,
        stream="Does not stream",
        last_recorded=(datetime.fromtimestamp(last / 10**9, UTC) if last else None),
    )


def _moment(value: str) -> str:
    """An ISO moment as a person reads it, to the minute in UTC."""
    if not value:
        return ""
    if len(value) == 10:
        return value
    return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _weekday(value: str) -> str:
    return date.fromisoformat(value).strftime("%a %d %b %Y") if value else ""


def matching(query: str, *texts: str) -> bool:
    """Whether every word of a search is in one of `texts`, case aside."""
    words = query.lower().split()
    held = " ".join(texts).lower()
    return all(word in held for word in words)


pages.environment.filters["moment"] = _moment
pages.environment.filters["day"] = _weekday


@pages.page(
    CONNECTION,
    "Connection",
    levels="admin",
    answers=records.ConnectionRead,
    name="read_connection",
    description=(
        "How this plugin reaches FRED, the St. Louis Fed's API, as every data plugin's "
        "Connection answers it: the mode (Live, Sample data or No key), whether FRED's API "
        "key is set (never its value), what FRED serves, its limit (120 requests a minute) "
        "and the requests made, the last call and why it failed if it did; it does not "
        "stream. Then FRED's own: each source -- the New York Fed's reference rates, the "
        "FOMC's target range, €STR, Treasury's par curves -- with its state, the latest day "
        "stated, its calls and last error; how many series are kept current; and how many "
        "answers are kept. No rate."
    ),
)
async def connection(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = connection_read(status, feed)
    return pages.answer("connection.html", read, detail=_state(status, feed)[2])


@pages.page(
    DATASETS,
    "Datasets",
    levels="admin",
    answers=records.DatasetsRead,
    name="read_datasets",
    description=(
        "What this plugin serves the lake, as every data plugin's Datasets answers it: its "
        "three datasets as the catalogue declares them (FRED's rate series by copyright "
        "class: public domain, citation required, pre-approval required; New York's day; "
        "no calendar), whether a deployment admin has licensed each, what it recorded and "
        "declined; the standing wants it keeps current and the wants it answered. Then "
        "FRED's own: the notice and citation its terms ask for, each dataset's lag between "
        "a rate's day and its publication, each rate and curve it records against with the "
        "deployment's record for it or why there is none, and each FRED series it carries "
        "with its copyright class, dataset, class changes and last update. No rate."
    ),
)
async def datasets(request: meridian.Request) -> meridian.Response:
    status, feed = _status()
    read = datasets_read(status, feed)
    # A browser's search narrows the series drawn, and it is drawn the latest
    # wants; a tool answers them all.
    query = request.query.get("q", "").strip()[:MOST_QUERY]
    asked = request.query.get("view", "")
    view = "series" if query else asked if asked in VIEWS else VIEWS[0]
    shown = [s for s in read.series if matching(query, s.series_id, s.of, s.title)]
    drawn = read if request.tool_name else replace(read, wants=read.wants[:SHOWN_WANTS])
    return pages.answer(
        "datasets.html",
        drawn,
        query=query,
        view=view,
        shown=shown,
        state=_state(status, feed),
        checked_at=_iso(status.checked_at),
        wants=len(read.wants),
    )
