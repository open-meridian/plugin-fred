"""The plugin's settings, declared to the SDK, and what it makes of them
(spec/a-public-rates-and-filings-data-plugin §4).

In the data role's order (spec/plugin-pages-follow-their-role): no
`environment` (FRED has one site); the credential; the plugin's own; then
the role's sample data.

- `fred_api_key` -- FRED's free API key, a secret, optional. Without it
  nothing is asked of FRED, and the three datasets show as not entitled at
  the vendor. Set through the dashboard's Settings form, never read back,
  displayed, logged or put in a page; an agent never types it.
- `fred_series` -- the series to keep current, a typed table: one column,
  the series' FRED ID, each cell one of the series this version carries
  (series.py), so the form checks every cell. Each series' copyright class
  and the dataset it is served under are FRED's to say, and the Datasets
  page's "FRED series" shows them, read from FRED. A series not listed is
  fetched when the lake wants it. Empty by default: each series carried
  duplicates its publisher's own plugin, the primary source (ruling 495),
  so a deployment chooses which FRED keeps current.
- `sample_data` -- a developer's setting: the responses committed under
  responses/ in place of FRED, for the e2e and for trying the plugin
  without a key.

The SDK declares the storage's two settings from the declaration's kind
(declaration.py): `responses_window_days` and `responses_past_window`.
Their names are the SDK's, and read here only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import meridian

from .raw import DEFAULT_WINDOW_DAYS, RESPONSES
from .series import CARRIED, carried

API_KEY = "fred_api_key"
SERIES = "fred_series"
#: The table's one column: a series' FRED ID.
SERIES_COLUMN = "series"
SAMPLE_DATA = "sample_data"
WINDOW = f"{RESPONSES}_window_days"
PAST_WINDOW = f"{RESPONSES}_past_window"


@meridian.settings
class Declared:
    """The settings as declared, in the data role's order: one typed class,
    the SDK's form, which `connect` and the declaration register."""

    fred_api_key: str = meridian.setting(
        "FRED API key",
        secret=True,
        description=(
            "Your free FRED API key, from fred.stlouisfed.org (My Account, API Keys). "
            "Without it the plugin asks FRED nothing."
        ),
    )
    fred_series: list = meridian.setting(  # type: ignore[type-arg]
        "Series kept current",
        description=(
            "The FRED series recorded as each is published. Any other series this "
            "plugin carries is fetched when a reader wants it."
        ),
        columns=[
            meridian.Column(
                SERIES_COLUMN,
                kind="choice",
                label="FRED series ID",
                required=True,
                description="The series' ID on FRED",
                choices=tuple(
                    meridian.Choice(s.series_id, s.series_id, f"{s.subject.name}, {s.point}")
                    for s in CARRIED
                ),
            )
        ],
        most_rows=len(CARRIED),
    )
    sample_data: bool = meridian.sample_data(
        description=(
            "Serve FRED's answers recorded on 23 October 2026, committed with the plugin, "
            "instead of asking FRED: every series it carries from 3 August to 22 October "
            "2026. No key needed. Development deployments only."
        )
    )


DECLARED = Declared


@dataclass(frozen=True)
class Config:
    key: str = field(default="", repr=False)
    series: tuple[str, ...] = ()
    sample_data: bool = False
    window_days: int = DEFAULT_WINDOW_DAYS
    past_window: str = "kept"


def _series(rows: object) -> tuple[str, ...]:
    """The table's series IDs, each one this version carries, once each, in
    the table's order."""
    held: list[str] = []
    if not isinstance(rows, Sequence) or isinstance(rows, str):
        return ()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        found = carried(str(row.get(SERIES_COLUMN, "")))
        if found is not None and found.series_id not in held:
            held.append(found.series_id)
    return tuple(held)


def config_from(values: Mapping[str, object]) -> Config:
    """The configuration a delivery of the settings says."""
    key = values.get(API_KEY)
    window = values.get(WINDOW)
    past = values.get(PAST_WINDOW)
    return Config(
        key=key.strip() if isinstance(key, str) else "",
        series=_series(values.get(SERIES)),
        sample_data=values.get(SAMPLE_DATA) is True,
        window_days=window if isinstance(window, int) and window > 0 else DEFAULT_WINDOW_DAYS,
        past_window=past if isinstance(past, str) and past else "kept",
    )
