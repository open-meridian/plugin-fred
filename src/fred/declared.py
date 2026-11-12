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
- its terms and pricing (contract 30, ruling 1032) its class's, in plain
  words (`TERMS`, by key), and no licence declared: FRED's API terms and
  notice, then what the class's copyright asks. A deployment's licence, set
  on the Data sources page, is the one enforced -- an unlicensed dataset is
  kept with each use right read restrictively, so `fred_restricted`'s
  words say its publisher's permission is needed to reproduce it; the
  plugin says nothing of whether a deployment meets anyone's terms. FRED's
  notice and each class's citation are also on the Datasets page's Terms
  tab and in docs/terms.md;
- a gap asked again (`gap_recovery` `backfill`, W10.14): FRED serves each
  series' history (three years for `fred_restricted`).

**Storage:** FRED's answers (raw.py), archivable, ten years by default.
"""

from __future__ import annotations

from meridian import DatasetDeclaration
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

#: FRED's terms, in plain words (contract 30, ruling 1032), as docs/terms.md
#: summarises them; then each copyright class's.
FRED_TERMS = (
    "FRED's API, from the Federal Reserve Bank of St. Louis: free, with a free API key. Its "
    "API terms of use ask for a notice that the product uses the FRED® API but is not "
    "endorsed or certified by the Federal Reserve Bank of St. Louis, and bar a use that "
    "replicates FRED's service. Copyright is each series' publisher's."
)
TERMS = {
    FRED_PUBLIC: FRED_TERMS
    + (" This dataset holds series FRED tags public domain: free to use, a citation requested."),
    FRED_CITED: FRED_TERMS
    + (
        " This dataset holds copyrighted series whose publishers require citation; using one "
        "beyond personal use needs its owner's permission, which FRED cannot grant (the New "
        "York Fed's terms for SOFR, EFFR and OBFR)."
    ),
    FRED_RESTRICTED: FRED_TERMS
    + (
        " This dataset holds copyrighted series whose publishers require pre-approval (ICE "
        "BofA's): FRED keeps three years of them, and reproducing them needs the owner's "
        "permission."
    ),
}


def _dataset(key: str, modes: list[str], history: int) -> DatasetDeclaration:
    return DatasetDeclaration(
        key=key,
        vendor=VENDOR,
        aggregator=AGGREGATOR,
        data_types=[RATE],
        modes=modes,
        cadence=CADENCE,
        history=history,
        terms_and_pricing=TERMS[key],
        gap_recovery="backfill",
        day_time_zone=DAY_TIME_ZONE,
        day_end_minute=DAY_END_MINUTE,
    )


CATALOGUE = [
    _dataset(FRED_PUBLIC, ["push", "pull"], 0),
    _dataset(FRED_CITED, ["push", "pull"], 0),
    _dataset(FRED_RESTRICTED, ["pull"], RESTRICTED_HISTORY),
]

RESPONSES_KIND = RecordKind(RESPONSES, "Raw responses", window_days=DEFAULT_WINDOW_DAYS)
