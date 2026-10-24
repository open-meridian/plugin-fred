"""The FRED series this version carries, and what each one is: the plugin's
FRED-ID map (spec/a-public-rates-and-filings-data-plugin §2, its Q4: "plugin-fred
keeps the FRED-ID map", as W10.1 keeps a pair's).

**The rates slice only** (§8, stage 1). Every series here is a rate series
whose subject the platform seeds as a referential record (§2, Q3; applied
with `seed_referential` on 2026-10-22), named by its administrator's code as a
source-scoped `symbol` -- never a FIGI guessed, never a record minted. A
series whose subject the platform does not seed (ICE BofA's spreads, the
prime rate, a mortgage rate) has no record to be recorded against yet, and
is not carried; FRED's macro series come with the series slice (stage 3).

- **The New York Fed's reference rates** -- SOFR, EFFR and OBFR, each a daily
  fixing with its 1st, 25th, 75th and 99th percentiles and its volume, which
  FRED publishes as companion series (SOFR1, SOFR25, SOFR75, SOFR99,
  SOFRVOL, ...); the SOFR 30, 90 and 180-day averages; the SOFR Index -- each
  against its `nyfed:` record.
- **The FOMC's target range**, its lower and upper bounds (DFEDTARL,
  DFEDTARU), against the two `frb:` records.
- **€STR** (ECBESTRVOLWGTTRMDMNRT), with its volume, against `ecb:ESTR`.
- **Treasury's par curves**, nominal and real: H.15's constant-maturity
  yields (DGS1MO to DGS30, DFII5 to DFII30), which "are read directly from
  the Treasury's daily par yield curve", each recorded against the curve's
  `ustreasury:` record with its tenor (§2: "DGS10 is Treasury's 10-year"),
  so FRED's point and Treasury's own sit under one subject and tenor, and
  the deployment's source priority chooses between them.

**Every one duplicates its publisher's own plugin** (`plugin-ny-fed`,
`plugin-fed-board`, `plugin-ecb`, `plugin-us-treasury`), which is the primary
source (ruling 495): the deployment's source priority puts the publisher's
dataset first, and FRED's is the fallback, with the longer history where
FRED has one (DGS10 from 1962; Treasury's par curve from 1990).

The kind, convention and tenor of each are the same the publisher's own
plugin records (`meridian.roles.data.rates`): a money-market fixing or
average is actual/360 simple; a par yield bond-equivalent, semi-annual.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from meridian.operations import RateConvention
from meridian.roles.data import rates

#: The administrators, as the platform's seeded records name them (the
#: symbol's source), and the publisher FRED states for each series.
NYFED, FRB, ECB, UST = "nyfed", "frb", "ecb", "ustreasury"
PUBLISHERS = {
    NYFED: "Federal Reserve Bank of New York",
    FRB: "Board of Governors of the Federal Reserve System (US)",
    ECB: "European Central Bank",
    UST: "Board of Governors of the Federal Reserve System (US)",
}

INTEREST_RATE, RATE_CURVE, INDEX = "interest_rate", "rate_curve", "index"


@dataclass(frozen=True)
class Subject:
    """A referential record, by the identifier the platform seeded it with:
    its administrator's code as a `symbol` at its source."""

    source: str
    code: str
    instrument_type: str
    description: str

    @property
    def identifier(self) -> tuple[str, str, str]:
        return ("symbol", self.code, self.source)

    @property
    def name(self) -> str:
        return f"{self.source}:{self.code}"


SOFR = Subject(NYFED, "SOFR", INTEREST_RATE, "Secured Overnight Financing Rate (SOFR)")
EFFR = Subject(NYFED, "EFFR", INTEREST_RATE, "Effective Federal Funds Rate (EFFR)")
OBFR = Subject(NYFED, "OBFR", INTEREST_RATE, "Overnight Bank Funding Rate (OBFR)")
SOFR_30 = Subject(NYFED, "SOFR 30-day average", INTEREST_RATE, "30-day Average SOFR")
SOFR_90 = Subject(NYFED, "SOFR 90-day average", INTEREST_RATE, "90-day Average SOFR")
SOFR_180 = Subject(NYFED, "SOFR 180-day average", INTEREST_RATE, "180-day Average SOFR")
SOFR_INDEX = Subject(NYFED, "SOFR Index", INDEX, "SOFR Index")
FOMC_LOWER = Subject(
    FRB,
    "FOMC target range lower bound",
    INTEREST_RATE,
    "Federal funds target range, lower bound (FOMC)",
)
FOMC_UPPER = Subject(
    FRB,
    "FOMC target range upper bound",
    INTEREST_RATE,
    "Federal funds target range, upper bound (FOMC)",
)
ESTR = Subject(ECB, "ESTR", INTEREST_RATE, "Euro short-term rate (€STR)")
PAR = Subject(
    UST, "Daily Treasury Par Yield Curve Rates", RATE_CURVE, "Daily Treasury par yield curve"
)
REAL = Subject(
    UST,
    "Daily Treasury Par Real Yield Curve Rates",
    RATE_CURVE,
    "Daily Treasury par real yield curve",
)

SUBJECTS = (
    SOFR, EFFR, OBFR, SOFR_30, SOFR_90, SOFR_180, SOFR_INDEX,
    FOMC_LOWER, FOMC_UPPER, ESTR, PAR, REAL,
)  # fmt: skip


@dataclass(frozen=True)
class Volume:
    """A companion series stating a fixing's volume: its FRED ID, the
    currency, and the units FRED states it in (billions of dollars,
    millions of euros) as a power of ten."""

    series_id: str
    currency: str
    exponent: int


@dataclass(frozen=True)
class Series:
    """One FRED series this version carries: its subject, what kind of rate
    it is, its convention, its tenor where it is a curve's point, and the
    companion series FRED states its percentiles and volume in."""

    series_id: str
    subject: Subject
    kind: str
    convention: RateConvention | None = None
    tenor: str = ""
    index_base: str = ""
    percentiles: Mapping[int, str] = field(default_factory=dict)
    volume: Volume | None = None

    @property
    def publisher(self) -> str:
        return PUBLISHERS[self.subject.source]

    @property
    def companions(self) -> tuple[str, ...]:
        """The companion series' IDs, percentiles first."""
        held = tuple(self.percentiles[p] for p in sorted(self.percentiles))
        return held + ((self.volume.series_id,) if self.volume else ())

    @property
    def point(self) -> str:
        """The series as a line names it: its tenor on its curve, or its kind."""
        return self.tenor or self.kind.replace("_", " ")


MM = rates.MONEY_MARKET
BEY = rates.BOND_EQUIVALENT


def _fixing(series_id: str, subject: Subject) -> Series:
    """A New York Fed fixing with FRED's 1st, 25th, 75th and 99th percentile
    and volume series (`SOFR1`, `SOFR25`, `SOFR75`, `SOFR99`, `SOFRVOL`)."""
    return Series(
        series_id,
        subject,
        "fixing",
        MM,
        percentiles={p: f"{series_id}{p}" for p in (1, 25, 75, 99)},
        volume=Volume(f"{series_id}VOL", "USD", 9),
    )


#: Treasury's nominal par curve by H.15's constant-maturity series, tenor by tenor.
_NOMINAL = {
    "DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M", "DGS1": "1Y", "DGS2": "2Y",
    "DGS3": "3Y", "DGS5": "5Y", "DGS7": "7Y", "DGS10": "10Y", "DGS20": "20Y", "DGS30": "30Y",
}  # fmt: skip
#: Its real par curve by H.15's inflation-indexed constant-maturity series.
_REAL = {"DFII5": "5Y", "DFII7": "7Y", "DFII10": "10Y", "DFII20": "20Y", "DFII30": "30Y"}

CARRIED: tuple[Series, ...] = (
    _fixing("SOFR", SOFR),
    _fixing("EFFR", EFFR),
    _fixing("OBFR", OBFR),
    Series("SOFR30DAYAVG", SOFR_30, "average", MM),
    Series("SOFR90DAYAVG", SOFR_90, "average", MM),
    Series("SOFR180DAYAVG", SOFR_180, "average", MM),
    # Money-market convention, as the publisher's plugin records the index:
    # the lake requires every rate's convention.
    Series("SOFRINDEX", SOFR_INDEX, "index_level", MM, index_base="2018-04-02=1.00000000"),
    Series("DFEDTARL", FOMC_LOWER, "fixing", MM),
    Series("DFEDTARU", FOMC_UPPER, "fixing", MM),
    Series(
        "ECBESTRVOLWGTTRMDMNRT",
        ESTR,
        "fixing",
        MM,
        volume=Volume("ECBESTRTOTVOL", "EUR", 6),
    ),
    *(Series(s, PAR, "par_yield", BEY, tenor=t) for s, t in _NOMINAL.items()),
    *(Series(s, REAL, "par_yield", BEY, tenor=t) for s, t in _REAL.items()),
)

BY_ID: dict[str, Series] = {s.series_id: s for s in CARRIED}


def carried(series_id: str) -> Series | None:
    """The series this version carries by its FRED ID, any case; None for
    one it does not."""
    return BY_ID.get(series_id.strip().upper())


def of_subject(subject: Subject) -> list[Series]:
    """The series recorded against one subject: one, or a curve's tenors."""
    return [s for s in CARRIED if s.subject == subject]
