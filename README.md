# meridian-fred

FRED's interest-rate series and headline index levels for
[Open Meridian](https://open-meridian.com): an Open Meridian plugin that
reads the St. Louis Fed's [FRED API](https://fred.stlouisfed.org/docs/api/fred/)
and puts the rate series it carries into a deployment's lake as rates, and
four indices' daily levels as their publishers' figures, each against the
reference record for it. It holds the `data` role, a data plugin.
This is release 0.5.0. How to set it up and use it is in
[docs/](docs/README.md); how a plugin like it is built is documented at
[open-meridian.dev](https://open-meridian.dev).

It is built on the SDK it pins, `open-meridian==0.37.0`, which declares
contract 30 (each dataset's terms in words and how a gap in it is
recovered); from contract v29 its work is one class for its role, registered with
`meridian.run` (each role one class); its feed delay is reported (ruling
518), and it records through the SDK's rates helpers
(`meridian.roles.data.rates`). It is FRED's plugin in meridian-design's
`spec/a-public-rates-and-filings-data-plugin.md`, with the rates slice
(§8, stage 1); FRED's macro series follow with the series slice.

## What it records

- **Three datasets, one per copyright class** (FRED's `cc` tag):
  `<instance>:fred_public` (public domain), `<instance>:fred_cited`
  (copyrighted, citation required), both pushed and pulled; and
  `<instance>:fred_restricted` (pre-approval required), pulled only, three
  years of history. Each serves `Rate` and, from 0.5.0, `DerivedSeries`
  (index levels); New York's day, ending at midnight;
  no calendar; no venue; a gap asked again of FRED's history (`backfill`).
  Each describes FRED's terms and its class's in words (contract 30, ruling
  1032: `declared.TERMS`) and declares no licence: the deployment admin
  licenses each on Data sources (served, never kept, suits
  `fred_restricted` without its publisher's permission); until one is set,
  the lake keeps the rows and reads every use right restrictively. A series
  whose class changes moves dataset.
- **Rate series only, each against a seeded record:**

  | Record (platform seed) | FRED series | Class |
  |---|---|---|
  | `nyfed:SOFR`, `nyfed:EFFR`, `nyfed:OBFR` | `SOFR`, `EFFR`, `OBFR`: fixings, with percentiles (`…1`, `…25`, `…75`, `…99`) and volume (`…VOL`) | cited |
  | `nyfed:SOFR 30/90/180-day average` | `SOFR30DAYAVG`, `SOFR90DAYAVG`, `SOFR180DAYAVG` | cited |
  | `nyfed:SOFR Index` | `SOFRINDEX`, an index level | cited |
  | `frb:FOMC target range lower/upper bound` | `DFEDTARL`, `DFEDTARU` | public |
  | `ecb:ESTR` | `ECBESTRVOLWGTTRMDMNRT`, with volume `ECBESTRTOTVOL` | public |
  | `ustreasury:Daily Treasury Par Yield Curve Rates` | `DGS1MO` … `DGS30`, eleven tenors | public |
  | `ustreasury:Daily Treasury Par Real Yield Curve Rates` | `DFII5` … `DFII30`, five tenors | public |

  Each duplicates its publisher's own plugin, the primary source (ruling
  495): the deployment's source priority chooses, FRED after the publisher.
- **Index levels as their publishers' figures** (0.5.0; ruling 955; the
  product owner, items 132 and 136): never a price or a rate, each a
  `DerivedSeries` named `level`, marked `published_by` the publisher FRED
  names, its rule the publisher's definition, against the index's
  referential record:

  | Record (proposed; not seeded yet) | FRED series | Class | Publisher |
  |---|---|---|---|
  | `spdji:SPX` | `SP500`, ten years on FRED | pre-approval | S&P Dow Jones Indices LLC |
  | `spdji:DJI` | `DJIA` | pre-approval | S&P Dow Jones Indices LLC |
  | `nasdaq:COMP` | `NASDAQCOM`, base 5 February 1971 = 100 | pre-approval | Nasdaq, Inc. |
  | `cboe:VIX` | `VIXCLS` | cited | Chicago Board Options Exchange |

  The platform seeds no index record yet: until a deployment holds one,
  its levels wait, reported missing, never minted. The pre-approval three
  are served when wanted, never pushed and never kept in the plugin's
  storage; each publisher's notice is in its dataset's terms.
- **The same kind, tenor and convention** the publisher's plugin records:
  a money-market fixing or average actual/360 simple, a par yield
  bond-equivalent; a curve's point against the curve's one record, with
  its tenor.
- **Exact.** Every value is a decimal from FRED's text. A "." is no row,
  never a zero.
- **Revisions as next versions**, a published time only where FRED's
  `last_updated` says it (the series' latest observation, first read).
- **Every subject resolved** by its administrator's code, a miss reported;
  nothing minted.
- **Every answer kept** as received, from the first day (but a restricted
  series' values), and named by each row it was first read into. The API
  key is never kept, logged or shown.

Its pages, under Manage alone, are the data role's: **Connection**
(`read_connection`: the key set or not, never its value; its Sources) and
**Datasets** (`read_datasets`: tabs Served with Lag, Wants, Records, FRED
series and Terms), each the same through the deployment's MCP, each fitting
one screen at 375, 582 and 1280 px, on its own and framed.

## Settings

- **FRED API key** (secret, optional): without it nothing is asked of FRED.
- **Series kept current** (`fred_series`, a typed table of FRED IDs, each a
  choice of the series carried): empty by default; others are fetched when
  wanted.
- **Sample data** (development deployments only), and the SDK's storage
  window settings.

## Checking it

    make ci-local                                  # lint, tests, plugin check, image, e2e: the pre-push gate
    make preview SHOTS=<dir>                       # each page in a browser with the kit, at 375, 582 and 1280 px, on its own and framed

`make e2e` runs it on core's plugin harness (core v27, a5da59a) beside a
reading plugin: with no key nothing asked or recorded; sample data and seven
series kept current recorded, each against the `INS-` record its
administrator's code resolves to on the harness's platform; both tools
answering what the pages show; licensed and entitled; SOFR and Treasury's
10-year read back as FRED states them; a past day wanted and recorded, a
holiday and a record FRED carries no series of declined; the lake as
`e2e/expected.lake`; and a new container recording nothing twice.

**The data suite.** `tests/test_suite.py` runs the SDK's suite on the
plugin's own conversion, and it passes: the rates slice's cases presented
but `two-conventions-one-tenor` (no bill series carried), and every case a
rates-only plugin never presents named with why (`RATES_NOT_PRESENTED`), and
`records-a-datasets-liveness` (it polls hourly and records no liveness);
from 0.5.0 it presents `records-a-derived-series` too, the VIX's level.

## The terms, summarised

Not legal advice; read FRED's own words before relying on them.

- **FRED's API terms**: a free key; the notice "This product uses the FRED®
  API but is not endorsed or certified by the Federal Reserve Bank of St.
  Louis"; no replicating FRED's service.
- **Copyright is per series**, and a copyrighted series is its publisher's:
  beyond personal use, its owner's permission. Each class is its own dataset
  so each deployment's licence is one decision.
- **The indices' publishers.** FRED's notes for `SP500` and `DJIA` say
  reproduction in any form is prohibited except with S&P Dow Jones Indices
  LLC's prior written permission; `NASDAQCOM` is Nasdaq's copyright,
  pre-approval required; `VIXCLS` is Cboe's, reprinted with permission,
  citation required. These are the deployment's to weigh, never a build
  gate: the plugin records the notices in its datasets' terms.

## Licence

Apache-2.0 (LICENSE, NOTICE). The responses under `src/fred/responses/` are
FRED's values, titles, update times and copyright tags as published on
2026-10-23, laid out as its API answers them (their `index.json` says how).
