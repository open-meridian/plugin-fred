"""FRED's rate series into the lake: the series kept current recorded as
FRED publishes them, and any series and day recorded when the lake wants it
(W10.4, W10.7), through the SDK's rates helpers (`meridian.roles.data.rates`,
contract v27; ruling 345).

**Push.** At start and every hour, each series kept current -- the
`fred_series` setting's, and a standing want's -- is checked: its tags once
a day, for its copyright class, which says its dataset (classes.py); then its
metadata, and only where FRED's `last_updated` moved since this process last
recorded it, its observations over the last ten days, with its companions'
(percentiles and volume). The lake answers each rate it holds unchanged, so
nothing is kept between starts but the answers in storage (decisions/028). A
restricted series is never pushed: its dataset is pulled only.

**Rates.** Each observation is one `Rate` row (rates.py of the SDK) against
its series' subject: a fixing with its percentiles and volume on the same
day, an average, an index level, or a curve's point with its tenor -- the
same kind, tenor and convention the publisher's own plugin records, so both
sit under one subject and the deployment's source priority. A value FRED
states as "." is no row, never a zero (`a-tenor-not-published`). Each is
read from FRED's text as a `Decimal`, never a float.

**Published time.** FRED states when it last changed a series
(`last_updated`), not when each value appeared. So a rate is given that time
only when it is the series' latest observation and first read now; a value
read from the history has none. A value FRED revises -- a fixing the
publisher corrects the same day -- is the same row key's next version, under
the later `last_updated` (`a-same-day-revision`). Where each rate was first
read, and the time noted then, is kept in storage (raw.py), so reading it
again names the same answer and time and the lake answers it unchanged.

**Subjects.** Each series' subject is a referential record the platform
seeds, resolved by its administrator's code (series.py) through the SDK's
`rates.Feed.subject`, once per process; one the deployment does not hold is
reported missing, once a day, and its series' rows wait. The plugin mints
nothing.

**Wants.** The lake asks a dataset for subjects: a business date, a range,
or the latest. Each subject the plugin carries a series of under that
dataset's class is answered from FRED, against the want; any other is
declined `not_covered`, a day before the series' first observation
`beyond_history`, a day FRED states nothing for `source_silent`, and every
subject `not_entitled` while no key is set.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import meridian
from meridian.operations import Money, Rate
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import Latency, data
from meridian.roles.data import rates

from . import api as fred
from .classes import RESTRICTED, class_of, dataset_of
from .declared import DAY_TIME_ZONE, KEYS, RATE, RESTRICTED_HISTORY
from .raw import First, RawStore
from .series import CARRIED, SUBJECTS, Series, Subject, carried, of_subject

log = logging.getLogger("fred")

#: The source this plugin names on what it reports missing, and its rows' series.
SOURCE = "fred"
#: The most days one want is answered for: a year.
MOST_DAYS = 366
#: How many published-minus-valid times are kept for the Lag column.
LAGS = 2000
NEW_YORK = ZoneInfo(DAY_TIME_ZONE)


def _ns(moment: datetime) -> int:
    return int(moment.timestamp() * 1_000_000) * 1000


def updated_ns(last_updated: str) -> int:
    """FRED's `last_updated` (`2026-10-23 07:02:03-05`) in nanoseconds; 0
    where it does not read."""
    try:
        return _ns(datetime.strptime(last_updated + "00", "%Y-%m-%d %H:%M:%S%z"))
    except ValueError:
        return 0


def number(text: str) -> Decimal | None:
    """A value as FRED states it, or None for "." and anything that does not
    read as a finite number."""
    try:
        read = Decimal(text.strip())
    except (InvalidOperation, AttributeError):
        return None
    return read if read.is_finite() else None


@dataclass
class SeriesState:
    """One series as the plugin last saw it."""

    series_id: str
    title: str = ""
    units: str = ""
    first_day: str = ""
    last_day: str = ""
    last_updated: str = ""
    #: Its copyright class, and the day the tags were read.
    copyright_class: str = ""
    classed_on: date | None = None
    #: Each change of class seen: (when, from, to).
    changes: list[tuple[str, str, str]] = field(default_factory=list)
    #: The `last_updated` this process last recorded it at.
    recorded_at: str = ""
    latest_day: date | None = None
    calls: int = 0
    error: str = ""


@dataclass
class SubjectState:
    """One subject as the plugin last saw it: the deployment's record for it,
    or why there is none."""

    subject: Subject
    instrument_id: str = ""
    miss: str = ""


@dataclass(frozen=True)
class Outcome:
    recorded: int = 0
    restated: int = 0
    unchanged: int = 0


@dataclass
class Status:
    """What the plugin last did, for its pages; held in memory, lost on a
    restart and read again by the first check."""

    mode: str = "live"
    keyed: bool = False
    started_at: datetime | None = None
    checked_at: datetime | None = None
    read_at: datetime | None = None
    error: str = ""
    fetches: int = 0
    series: dict[str, SeriesState] = field(default_factory=dict)
    subjects: dict[str, SubjectState] = field(default_factory=dict)
    #: Values that named a rate but did not read, each with how often seen.
    unread: dict[str, int] = field(default_factory=dict)
    #: Published minus valid-from, in seconds, by dataset key.
    lags: dict[str, list[int]] = field(default_factory=dict)


class Failed(Exception):  # noqa: N818 - what an answer was
    """FRED refused or did not answer; its words."""


class Feed:
    """The plugin's work, on its typed operations -- `plugin` is the
    connected `meridian.Plugin`, or the suite's `Recorder` in its tests --
    reading FRED, resolving, recording, answering wants."""

    def __init__(
        self,
        plugin: Any,
        api: fred.Api,
        raw: RawStore,
        now: Callable[[], datetime] = fred.utc_now,
        kept: Sequence[str] = (),
        keyed: bool = False,
    ) -> None:
        self.plugin = plugin
        self.api = api
        self.raw = raw
        self.now = now
        self.kept = tuple(kept)
        clock = lambda: _ns(self.now())  # noqa: E731 - one clock for both
        self.wants = data.Wants(plugin, KEYS, clock_ns=clock)
        # Contract v28 (ruling 518): each rate recorded unasked or for a
        # standing want has its age at the edge recorded where it states a
        # published time, reported every 10 seconds (`__main__`).
        self.latency = Latency(plugin, clock_ns=clock)
        self.wants.latency = self.latency
        self.rates = rates.Feed(
            plugin, SOURCE, wants=self.wants, day_zone=DAY_TIME_ZONE, clock_ns=clock
        )
        self.status = Status(mode=api.mode, keyed=keyed, started_at=now())
        for subject in SUBJECTS:
            self.status.subjects[subject.name] = SubjectState(subject)

    def use(self, api: fred.Api, kept: Sequence[str], keyed: bool) -> None:
        """Read from `api` from now on, keeping `kept` current: the settings
        changed."""
        if api.mode != self.api.mode or keyed != self.status.keyed:
            for held in self.status.series.values():
                held.recorded_at = ""
        self.api = api
        self.kept = tuple(kept)
        self.status.mode = api.mode
        self.status.keyed = keyed

    @property
    def answering(self) -> bool:
        """Whether FRED may be asked: a key set, or sample data."""
        return self.status.keyed or self.api.mode == "synthetic"

    def today(self) -> date:
        return self.api.today(self.now().astimezone(NEW_YORK))

    def state(self, series_id: str) -> SeriesState:
        return self.status.series.setdefault(series_id, SeriesState(series_id))

    # ── Asking FRED ─────────────────────────────────────────────────────

    async def ask(self, path: str, series_id: str, keep: bool = True) -> tuple[dict[str, Any], str]:
        """One answer's JSON and its key in storage (empty where not kept);
        Failed where FRED refused or did not answer."""
        held = self.state(series_id)
        try:
            fetched = await self.api.get(path)
        except fred.NoKey as none:
            raise Failed(str(none)) from none
        except fred.Unreachable as failed:
            held.error = str(failed)
            raise Failed(str(failed)) from failed
        self.status.fetches += 1
        held.calls += 1
        key = self.raw.keep(fetched) if keep else ""
        if fetched.status != 200:
            held.error = fetched.error
            raise Failed(fetched.error)
        held.error = ""
        return fetched.json(), key

    async def classify(self, series: str) -> str:
        """A series' copyright class, from its tags, read once a day."""
        held = self.state(series)
        today = self.today()
        if held.copyright_class and held.classed_on == today:
            return held.copyright_class
        answer, _ = await self.ask(fred.tags_path(series), series)
        found = class_of(answer)
        if held.copyright_class and found and found != held.copyright_class:
            held.changes.append(
                (self.now().isoformat(timespec="seconds"), held.copyright_class, found)
            )
            held.recorded_at = ""
            log.info("%s's class changed from %s to %s", series, held.copyright_class, found)
        held.copyright_class, held.classed_on = found, today
        return found

    async def describe(self, series: str) -> SeriesState:
        """A series' metadata: its title, units, range and `last_updated`."""
        held = self.state(series)
        answer, _ = await self.ask(fred.series_path(series), series)
        stated = (answer.get("seriess") or [{}])[0]
        held.title = str(stated.get("title", held.title))
        held.units = str(stated.get("units", held.units))
        held.first_day = str(stated.get("observation_start", held.first_day))
        held.last_day = str(stated.get("observation_end", held.last_day))
        held.last_updated = str(stated.get("last_updated", held.last_updated))
        return held

    async def observations(
        self, series: str, start: date, end: date, keep: bool
    ) -> tuple[dict[date, str], str]:
        """A series' values from `start` to `end`, by day, as FRED states
        them, and the answer's key in storage."""
        answer, key = await self.ask(fred.observations_path(series, start, end), series, keep)
        values: dict[date, str] = {}
        for observation in answer.get("observations", []):
            try:
                values[date.fromisoformat(str(observation["date"]))] = str(observation["value"])
            except (KeyError, ValueError):
                continue
        return values, key

    # ── Resolving ───────────────────────────────────────────────────────

    async def subject(self, subject: Subject) -> str:
        """The deployment's record for a subject, resolved once per process
        by the SDK; empty, reported missing, where none is held."""
        held = self.status.subjects.setdefault(subject.name, SubjectState(subject))
        if held.instrument_id:
            return held.instrument_id
        found = await self.rates.subject(
            subject.identifier,
            description=subject.description,
            instrument_type=subject.instrument_type,
        )
        held.instrument_id, held.miss = found, "" if found else "not held"
        return found

    async def subjects_held(self) -> dict[str, Subject]:
        """Every subject carried, by the record each resolves to."""
        held: dict[str, Subject] = {}
        for subject in SUBJECTS:
            found = await self.subject(subject)
            if found:
                held[found] = subject
        return held

    # ── Converting and recording ────────────────────────────────────────

    def convert(
        self,
        series: Series,
        subject_id: str,
        key: str,
        values: dict[str, dict[date, str]],
        raw_key: str,
        days: Iterable[date],
        published: tuple[date | None, int],
        keep: bool = True,
    ) -> list[Rate]:
        """`series`' rows on `days` under the dataset `key`: one per day it
        states a value, with the companions' percentiles and volume that day.
        `published` is the series' latest observation's day and FRED's
        `last_updated`, given to that day's row where first read now. A
        series not kept (restricted) names no raw record and notes nothing."""
        rows: list[Rate] = []
        main = values.get(series.series_id, {})
        latest, updated = published
        for day in sorted(set(days)):
            text = main.get(day, ".")
            value = number(text)
            if value is None:
                if text.strip() not in (".", ""):
                    line = f"{series.series_id} {day}: {text[:40]!r}"
                    self.status.unread[line] = self.status.unread.get(line, 0) + 1
                continue
            percentiles = {
                p: v
                for p, companion in series.percentiles.items()
                if (v := number(values.get(companion, {}).get(day, "."))) is not None
            }
            volume = None
            if series.volume is not None:
                stated = number(values.get(series.volume.series_id, {}).get(day, "."))
                if stated is not None:
                    volume = Money(
                        stated.scaleb(series.volume.exponent), currency_code=series.volume.currency
                    )
            amount = (
                rates.index_level(value, series.index_base)
                if series.kind == "index_level"
                else rates.percent(value)
            )
            given: dict[str, Any] = dict(
                business_date=day,
                convention=series.convention,
                tenor=series.tenor or None,
                volume=volume,
                percentiles=percentiles,
            )
            row = self.rates.rate(subject_id, key, series.kind, amount, **given)
            said = "|".join(
                [text.strip(), *(f"{p}:{v}" for p, v in sorted(percentiles.items())),
                 str(volume.amount) if volume else ""]
            )  # fmt: skip
            noted = updated if day == latest else 0
            row_key = row.meta.row_key if row.meta is not None else ""
            if keep:
                first, fresh = self.raw.first(row_key, day, said, raw_key, noted)
            else:
                first, fresh = First("", noted), False
            if fresh and first.published_ns:
                start = datetime.combine(day, datetime.min.time(), NEW_YORK)
                lag = (first.published_ns - _ns(start)) // 10**9
                held = self.status.lags.setdefault(key, [])
                held[:] = [*held[-(LAGS - 1) :], lag]
            rows.append(
                self.rates.rate(
                    subject_id,
                    key,
                    series.kind,
                    amount,
                    published_ns=first.published_ns,
                    raw_key=first.key,
                    **given,
                )
            )
        return rows

    async def refresh(
        self,
        series: Series,
        start: date,
        end: date,
        *,
        want_id: str = "",
        dataset: str = "",
        only_changed: bool = False,
    ) -> Outcome:
        """Read one series from `start` to `end` and record it under its
        class's dataset -- `dataset`, where a want names one, or nothing if
        its class says another -- against `want_id` where given. With
        `only_changed`, nothing is read past its metadata where FRED has not
        changed it since this process recorded it. Failed where FRED did not
        answer."""
        copyright_class = await self.classify(series.series_id)
        key = dataset_of(copyright_class)
        if not key or (dataset and key != dataset):
            return Outcome()
        if not want_id and copyright_class == RESTRICTED:
            return Outcome()
        subject_id = await self.subject(series.subject)
        if not subject_id:
            return Outcome()
        held = await self.describe(series.series_id)
        if only_changed and held.last_updated and held.last_updated == held.recorded_at:
            return Outcome()
        keep = copyright_class != RESTRICTED
        values: dict[str, dict[date, str]] = {}
        main, raw_key = await self.observations(series.series_id, start, end, keep)
        values[series.series_id] = main
        for companion in series.companions:
            values[companion], _ = await self.observations(companion, start, end, keep)
        stated = sorted(d for d, v in main.items() if number(v) is not None)
        if stated:
            held.latest_day = max(stated[-1], held.latest_day or stated[-1])
        latest = date.fromisoformat(held.last_day) if held.last_day else None
        rows = self.convert(
            series,
            subject_id,
            key,
            values,
            raw_key,
            main.keys(),
            (latest, updated_ns(held.last_updated)),
            keep,
        )
        self.raw.save_firsts()
        counts = self.wants.counts
        before = (counts.recorded, counts.restated, counts.unchanged)
        if rows:
            await self.rates.record(key, rows, want_id)
        if not want_id:
            held.recorded_at = held.last_updated
        return Outcome(
            counts.recorded - before[0], counts.restated - before[1], counts.unchanged - before[2]
        )

    def current_series(self) -> list[Series]:
        """The series kept current: the setting's, then each standing want's."""
        named = [carried(s) for s in self.kept]
        held = [s for s in named if s is not None]
        for standing in self.wants.standing.values():
            for subject in standing.subjects:
                found = self.status.subjects.get(self._name_of(subject))
                if found is not None:
                    held.extend(s for s in of_subject(found.subject) if s not in held)
        return held

    def _name_of(self, instrument_id: str) -> str:
        for name, held in self.status.subjects.items():
            if held.instrument_id == instrument_id:
                return name
        return ""

    async def check(self) -> Outcome:
        """Read every series kept current, recording what FRED changed."""
        self.status.checked_at = self.now()
        if not self.answering:
            self.status.error = ""
            return Outcome()
        start, end = fred.current(self.api, self.now().astimezone(NEW_YORK))
        done = [0, 0, 0]
        errors: list[str] = []
        kept = self.current_series()
        for series in kept:
            try:
                outcome = await self.refresh(series, start, end, only_changed=True)
            except Failed as failed:
                errors.append(f"{series.series_id}: {failed}")
                continue
            done = [done[0] + outcome.recorded, done[1] + outcome.restated,
                    done[2] + outcome.unchanged]  # fmt: skip
        self.status.error = errors[0] if errors else ""
        if kept and len(errors) < len(kept):
            self.status.read_at = self.now()
        if any(done):
            log.info("%d recorded, %d restated, %d unchanged", *done)
        return Outcome(*done)

    # ── Wants ───────────────────────────────────────────────────────────

    async def on_want(self, heard: meridian.Heard[ops.ObservationsWantedEvent]) -> None:
        """Record what the lake wants of one of the plugin's datasets, or
        decline it (the SDK's `Wants.hear`, answered by `answer`)."""
        await self.wants.hear(heard, self.answer)

    async def on_withdrawn(self, heard: meridian.Heard[ops.WantWithdrawnEvent]) -> None:
        """A standing want withdrawn: no longer kept current."""
        self.wants.withdraw(heard.message.want_id)
        log.info("standing want %s withdrawn", heard.message.want_id)

    def _days(self, want: ops.ObservationsWantedEvent) -> list[date]:
        if want.business_date:
            return [date.fromisoformat(want.business_date)]
        if want.valid_from_ns or want.valid_until_ns:
            start = datetime.fromtimestamp(want.valid_from_ns / 1e9, NEW_YORK).date()
            until = want.valid_until_ns - 1 if want.valid_until_ns else _ns(self.now())
            end = datetime.fromtimestamp(until / 1e9, NEW_YORK).date()
            days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
            return days[-MOST_DAYS:]
        start, end = fred.current(self.api, self.now().astimezone(NEW_YORK))
        return [start + timedelta(days=n) for n in range((end - start).days + 1)]

    async def answer(
        self,
        want: ops.ObservationsWantedEvent,
        key: str,
        subjects: list[str],
        kinds: tuple[int, ...],
    ) -> dict[str, str]:
        """One want answered from FRED: its rates recorded against it, and
        each subject declined, with why."""
        if key not in KEYS or want.data_type not in ("", RATE):
            return {s: "not_covered" for s in subjects}
        if not self.answering:
            return {s: "not_entitled" for s in subjects}
        held = await self.subjects_held()
        declined: dict[str, str] = {}
        days = self._days(want)
        for subject_id in subjects:
            subject = held.get(subject_id)
            if subject is None:
                declined[subject_id] = "not_covered"
                continue
            reason = await self._record_subject(want, key, subject, days)
            if reason:
                declined[subject_id] = reason
            elif want.standing:
                self.wants.stand(want, [subject_id], kinds)
        return declined

    async def _record_subject(
        self, want: ops.ObservationsWantedEvent, key: str, subject: Subject, days: list[date]
    ) -> str:
        """Record a subject's series on `days` against the want; the reason it
        is declined, or empty where a rate was recorded."""
        today = self.today()
        mine: list[Series] = []
        for series in of_subject(subject):
            try:
                if dataset_of(await self.classify(series.series_id)) == key:
                    mine.append(series)
            except Failed as failed:
                log.warning(
                    "want %s: %s not classified: %s", want.want_id, series.series_id, failed
                )
                return "source_silent"
        if not mine:
            return "not_covered"
        asked = [d for d in days if d <= today]
        if key == dataset_of(RESTRICTED):
            oldest = today - timedelta(days=RESTRICTED_HISTORY)
            if asked and all(d < oldest for d in asked):
                return "beyond_history"
            asked = [d for d in asked if d >= oldest]
        if not asked:
            return "source_silent"
        sent = 0
        for series in mine:
            try:
                await self.describe(series.series_id)
                first = self.state(series.series_id).first_day
                if first and all(d.isoformat() < first for d in asked):
                    continue
                done = await self.refresh(
                    series, min(asked), max(asked), want_id=want.want_id, dataset=key
                )
            except Failed as failed:
                log.warning("want %s: %s not read: %s", want.want_id, series.series_id, failed)
                continue
            sent += done.recorded + done.restated + done.unchanged
        if sent:
            return ""
        firsts = [self.state(s.series_id).first_day for s in mine]
        if all(f and all(d.isoformat() < f for d in asked) for f in firsts):
            return "beyond_history"
        return "source_silent"


#: Every series ID this version may ask FRED for, companions among them.
ASKED = frozenset(s.series_id for s in CARRIED) | frozenset(
    c for s in CARRIED for c in s.companions
)
