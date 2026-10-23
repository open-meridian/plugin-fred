"""The typed records the pages answer, for a person's page and an agent's
tool alike (contract v12; spec/a-deployment-serves-its-mcp): the data role's
common records (`meridian.roles.data`, spec/plugin-pages-follow-their-role),
each extended with FRED's own fields under the names
spec/a-public-rates-and-filings-data-plugin §5 gives its vendor sections:
Connection's **Sources**, and Datasets' **Records**, **FRED series** and
**Lag**. The Connection tab is `read_connection`, the Datasets tab
`read_datasets`, each answering what its page shows, as data, under the
role's names.

A data plugin's pages show its connection and its datasets, never a rate
(plans/the-lake-prices-the-book, ruled 2026-10-03): rates are the reading
roles'. So neither record holds a value; each says how FRED was reached and
what the plugin serves of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meridian.roles import data


@dataclass(frozen=True)
class SourceRead:
    """One source the plugin reads, as "Sources" lists it: the publisher's
    rates FRED carries, their state, the latest day stated, the next
    expected (none: FRED's datasets declare no calendar), the calls made for
    them, and the last error."""

    source: str
    publisher: str
    series: int
    state: str
    last_release: str = ""
    next_expected: str = ""
    calls: int = 0
    last_error: str = ""


@dataclass(frozen=True)
class ConnectionRead(data.ConnectionRead):
    """Connection's common fields, then FRED's: the head's status and what it
    means, where it reads, the last check, each source as "Sources" lists it,
    how many series are kept current, and the answers kept."""

    #: The head's status: `ok`, `busy`, `warn` or `error`, and what it means.
    state: str = ""
    said: str = ""
    source: str = ""
    checked_at: str = ""
    kept_current: int = 0
    sources: list[SourceRead] = field(default_factory=list)
    responses_kept: int = 0
    kept_for: str = ""


@dataclass(frozen=True)
class RecordRead:
    """One rate or curve the plugin records against, as "Records" lists it:
    the platform's seeded record by its administrator's code, its type, the
    series recorded against it, and the deployment's record or why there is
    none."""

    name: str
    description: str
    instrument_type: str
    series: list[str]
    instrument_id: str
    miss: str


@dataclass(frozen=True)
class SeriesRead:
    """One FRED series the plugin carries, as "FRED series" lists it: what
    it is a rate of, FRED's title, its copyright class and the dataset it is
    served under, each change of class seen, whether it is kept current, its
    first observation, and FRED's last update."""

    series_id: str
    of: str
    title: str = ""
    copyright_class: str = ""
    dataset: str = ""
    changes: list[str] = field(default_factory=list)
    kept_current: bool = False
    first_day: str = ""
    latest_day: str = ""
    last_updated: str = ""
    last_error: str = ""


@dataclass(frozen=True)
class LagRead:
    """A dataset's lag: published minus valid time for its rates first read
    with their published time since the plugin started -- the median and
    the longest, in seconds and in words -- and how many."""

    dataset: str
    rates: int = 0
    median_seconds: int = 0
    longest_seconds: int = 0
    #: The median, and the whole, in words.
    median: str = ""
    said: str = ""


@dataclass(frozen=True)
class DatasetsRead(data.DatasetsRead):
    """Datasets' common fields, then FRED's: the notices its terms ask for,
    each record it records against ("Records"), each series it carries
    ("FRED series"), each dataset's lag ("Lag"), and the values it could not
    read. Its rows are the role's."""

    served: list[data.Served] = field(default_factory=list)
    wants: list[data.WantHeard] = field(default_factory=list)  # type: ignore[assignment]
    attribution: str = ""
    records: list[RecordRead] = field(default_factory=list)
    series: list[SeriesRead] = field(default_factory=list)
    lag: list[LagRead] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)
