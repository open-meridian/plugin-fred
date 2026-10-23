"""What this version declares beside its role, `data` (W8.1, W4.1; the
catalogue from contract v18), built from code and used twice: `__main__`
registers with it, and `meridian plugin upload` reads it from the built image
(pyproject.toml's `[tool.meridian] declaration`).

**The catalogue: three datasets, one per copyright class** (spec/a-public-
rates-and-filings-data-plugin §3 and its Q9, the keys approved with the
batch, 2026-10-14), each serving rates (contract v27's `Rate`) from FRED's
rate series. Observations, the macro series' kind, join them with the
series slice (§8, stage 3); this version declares only what it records.

- `vendor` each series' publisher, as FRED states it (§3: "each series'
  publisher, as the series states it"), and `aggregator` FRED;
- `modes`: `fred_public` and `fred_cited` are pushed (the series kept
  current, the `fred_series` setting) and pulled (any day, on a want);
  `fred_restricted` is pulled only;
- `cadence` a day: the rate series carried are daily;
- `history` 0, "as each series states" (the Datasets page says each
  series' first observation), and `fred_restricted` three years, 1,095
  days, since ICE's series keep only three on FRED;
- its day New York's, ending at midnight, and no calendar: each series
  follows its publisher's, which FRED does not state (§3: "none");
- no venue;
- the licence each class's terms suggest (§7): `fred_public` and
  `fred_cited` kept, derived use and display; `fred_restricted` served, never
  kept, no derived use, display. A deployment's licence confirms or replaces
  each default on the Data sources page; the plugin says nothing of whether
  a deployment meets anyone's terms. FRED's non-endorsement notice, and the
  citation the cited class requires, are stated in docs/terms.md and on the
  Datasets page: SDK 0.32.1's `DatasetLicence` does not carry contract
  v27's attribution fields yet (`attribution_text`, `copyright_class`).

**Storage:** FRED's answers (raw.py), archivable, ten years by default.
"""

from __future__ import annotations

from meridian import DatasetDeclaration, DatasetLicence
from meridian.declaration import RecordKind

from .classes import DATASETS, PUBLIC, RESTRICTED
from .raw import DEFAULT_WINDOW_DAYS, RESPONSES

FRED_PUBLIC = DATASETS[PUBLIC]
FRED_CITED = DATASETS["cited"]
FRED_RESTRICTED = DATASETS[RESTRICTED]
KEYS = (FRED_PUBLIC, FRED_CITED, FRED_RESTRICTED)

VENDOR = "Each series' publisher, as FRED states it"
AGGREGATOR = "FRED, Federal Reserve Bank of St. Louis"
RATE = "meridian.v1.Rate"
#: A day, in seconds.
CADENCE = 86_400
#: ICE BofA's series keep three years on FRED (since April 2026).
RESTRICTED_HISTORY = 1_095
DAY_TIME_ZONE = "America/New_York"
DAY_END_MINUTE = 0

_KEPT = DatasetLicence(kept=True, derived_use_terms="not_restricted", display=True)
_SERVED = DatasetLicence(kept=False, derived_use_terms="internal_only", display=True)


def _dataset(
    key: str, modes: list[str], history: int, licence: DatasetLicence
) -> DatasetDeclaration:
    return DatasetDeclaration(
        key=key,
        vendor=VENDOR,
        aggregator=AGGREGATOR,
        data_types=[RATE],
        modes=modes,
        cadence=CADENCE,
        history=history,
        licence_default=licence,
        day_time_zone=DAY_TIME_ZONE,
        day_end_minute=DAY_END_MINUTE,
    )


CATALOGUE = [
    _dataset(FRED_PUBLIC, ["push", "pull"], 0, _KEPT),
    _dataset(FRED_CITED, ["push", "pull"], 0, _KEPT),
    _dataset(FRED_RESTRICTED, ["pull"], RESTRICTED_HISTORY, _SERVED),
]

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)
