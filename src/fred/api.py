"""The St. Louis Fed's FRED API, and its stand-in.

Three requests are made, and nothing else, each as JSON:

- `/fred/series?series_id=<id>` -- a series' metadata: its title, units,
  frequency, first and last observation, and `last_updated`, when FRED last
  changed it, which the plugin reads first so an hour with nothing new costs
  one small answer per series;
- `/fred/series/tags?series_id=<id>` -- its tags, among them its copyright
  class (the `cc` group: public domain, citation required, pre-approval
  required), which says which of the plugin's datasets it is served under
  (classes.py), read once a day;
- `/fred/series/observations?series_id=<id>&observation_start=<day>&observation_end=<day>`
  -- its values over a range of days, each a string, "." where FRED states
  none.

**The key.** Every request carries FRED's free API key, the plugin's one
secret setting, as `api_key`. It is added to the request as it is sent and
nowhere else: the address an answer is kept under, a log line, an error and
a page never hold it (`redacted`). Without a key nothing is asked.

**Limits.** FRED allows 120 requests a minute for a key; the plugin asks one
at a time, at most one a second, and says who it is in its User-Agent. A 429
is counted and waited out on the next check.

`SyntheticApi` answers from the responses committed under responses/
(responses/index.json): every carried series' metadata, tags and
observations from 3 August to 22 October 2026, and Treasury's nominal curve
around the 1-month's first day, 31 July 2001. A request for a range is answered with the
recorded observations in it, so the plugin's tests and sample data run on
it, offline, the same on any day.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from importlib import resources
from typing import Any, Protocol

BASE = "https://api.stlouisfed.org"
SERIES = "/fred/series"
TAGS = "/fred/series/tags"
OBSERVATIONS = "/fred/series/observations"
USER_AGENT = "meridian-fred (+https://github.com/open-meridian/plugin-fred)"
#: The least time between two requests, in seconds: FRED allows 120 a minute.
SPACING = 1.0
TIMEOUT = 60.0
#: The most of an answer read: a series' daily history since 1962 is ~1 MB.
MOST_BYTES = 16 * 1024 * 1024
#: How many days the current range reaches back: a revision of the last week
#: or so is read as the same row's next version.
CURRENT_DAYS = 10


def series_path(series_id: str) -> str:
    return f"{SERIES}?series_id={urllib.parse.quote(series_id)}&file_type=json"


def tags_path(series_id: str) -> str:
    return f"{TAGS}?series_id={urllib.parse.quote(series_id)}&file_type=json"


def observations_path(series_id: str, start: date, end: date) -> str:
    return (
        f"{OBSERVATIONS}?series_id={urllib.parse.quote(series_id)}"
        f"&observation_start={start.isoformat()}&observation_end={end.isoformat()}"
        "&file_type=json"
    )


def redacted(text: str, key: str) -> str:
    """`text` with the key, wherever it appears, said as `***`."""
    return text.replace(key, "***") if key else text


class Unreachable(Exception):  # noqa: N818 - what FRED was
    """FRED could not be asked: no answer, or not in time."""


class NoKey(Exception):  # noqa: N818 - what the plugin lacks
    """No API key is set, so FRED is not asked."""


@dataclass(frozen=True)
class Fetched:
    """One answer of FRED's, as received; `path` never holds the key."""

    path: str
    status: int
    body: bytes
    fetched_at: datetime

    @property
    def url(self) -> str:
        return BASE + self.path

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> dict[str, Any]:
        """The answer's JSON object; empty where it holds none."""
        try:
            read = json.loads(self.body)
        except ValueError:
            return {}
        return read if isinstance(read, dict) else {}

    @property
    def error(self) -> str:
        """FRED's own words for a refusal, or the status."""
        said = self.json().get("error_message")
        return str(said) if said else f"{self.url} answered {self.status}"


class Api(Protocol):
    mode: str
    rate_limited: int

    def today(self, now: datetime) -> date: ...

    async def get(self, path: str) -> Fetched: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


class LiveApi:
    """FRED itself, asked with `key`."""

    mode = "live"

    def __init__(self, key: str, now: Callable[[], datetime] = utc_now) -> None:
        self._key = key
        self._now = now
        self._lock = asyncio.Lock()
        self._last = 0.0
        self.rate_limited = 0

    def today(self, now: datetime) -> date:
        return now.date()

    async def get(self, path: str) -> Fetched:
        if not self._key:
            raise NoKey("no FRED API key is set")
        async with self._lock:
            wait = self._last + SPACING - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                got = await asyncio.to_thread(self._get, path)
            finally:
                self._last = time.monotonic()
        if got.status == 429:
            self.rate_limited += 1
        return got

    def _get(self, path: str) -> Fetched:
        keyed = f"{BASE}{path}&api_key={urllib.parse.quote(self._key)}"
        request = urllib.request.Request(
            keyed, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310 - FRED's https address
                body = answer.read(MOST_BYTES + 1)
                status = answer.status
        except urllib.error.HTTPError as refused:
            body = refused.read(MOST_BYTES + 1) if refused.fp else b""
            status = refused.code
        except (urllib.error.URLError, TimeoutError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            # The reason's type alone: its words may hold the address, key and all.
            raise Unreachable(f"{BASE}{path}: {type(reason).__name__}") from failed
        if len(body) > MOST_BYTES:
            raise Unreachable(f"{BASE}{path}: answered more than {MOST_BYTES} bytes")
        clean = redacted(body.decode("utf-8", errors="replace"), self._key).encode()
        return Fetched(path, status, clean, self._now())


def _query(path: str) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(path.split("?", 1)[1])) if "?" in path else {}


def _refused(path: str, words: str, at: datetime) -> Fetched:
    body = json.dumps({"error_code": 400, "error_message": f"Bad Request.  {words}"})
    return Fetched(path, 400, body.encode(), at)


class SyntheticApi:
    """The responses committed under responses/: each request answered as
    FRED answered it, a range of observations with the recorded ones in it."""

    mode = "synthetic"

    def __init__(self, now: Callable[[], datetime] = utc_now) -> None:
        self._now = now
        held = resources.files(__package__).joinpath("responses")
        index = json.loads(held.joinpath("index.json").read_text(encoding="utf-8"))
        recorded = json.loads(gzip.decompress(held.joinpath(index["file"]).read_bytes()))
        self.series: dict[str, dict[str, Any]] = recorded["series"]
        self.tags: dict[str, dict[str, Any]] = recorded["tags"]
        self.observations: dict[str, dict[str, Any]] = recorded["observations"]
        self.last_day = date.fromisoformat(index["last_day"])
        self.recorded_on = str(index["recorded_on"])
        self.asked: list[str] = []
        self.rate_limited = 0

    def today(self, now: datetime) -> date:
        """The recording's last day, whatever the clock says."""
        return self.last_day

    async def get(self, path: str) -> Fetched:
        self.asked.append(path)
        at = self._now()
        query = _query(path)
        series_id = query.get("series_id", "")
        route = path.split("?", 1)[0]
        held = {SERIES: self.series, TAGS: self.tags, OBSERVATIONS: self.observations}.get(route)
        if held is None:
            return Fetched(path, 404, b"Not Found", at)
        if series_id not in held:
            return _refused(path, "The series does not exist.", at)
        answer = dict(held[series_id])
        if route == OBSERVATIONS:
            start = query.get("observation_start", "1776-07-04")
            end = query.get("observation_end", "9999-12-31")
            kept = [o for o in answer["observations"] if start <= o["date"] <= end]
            answer.update(
                observation_start=start, observation_end=end, count=len(kept), observations=kept
            )
        return Fetched(path, 200, json.dumps(answer).encode(), at)


def api(synthetic: bool, key: str, now: Callable[[], datetime] = utc_now) -> Api:
    return SyntheticApi(now) if synthetic else LiveApi(key, now)


def current(api: Api, now: datetime) -> tuple[date, date]:
    """The current range: the last `CURRENT_DAYS` days to the API's today."""
    today = api.today(now)
    return today - timedelta(days=CURRENT_DAYS), today
