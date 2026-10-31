# meridian-fred

FRED's interest-rate series for [Open Meridian](https://open-meridian.com):
an Open Meridian plugin that reads the St. Louis Fed's
[FRED API](https://fred.stlouisfed.org/docs/api/fred/) and puts the rate
series it carries into a deployment's lake as rates, each against the
platform's reference record for it. It holds the `data` role, a data plugin.
This is release 0.2.0. How to set it up and use it is in
[docs/](docs/README.md); how a plugin like it is built is documented at
[open-meridian.dev](https://open-meridian.dev).

It is built on the SDK it pins, `open-meridian==0.33.4`, which declares
contract v28 (its feed delay reported, ruling 518), and records through the SDK's rates helpers
(`meridian.roles.data.rates`). It is FRED's plugin in meridian-design's
`spec/a-public-rates-and-filings-data-plugin.md`, with the rates slice
(§8, stage 1); FRED's macro series follow with the series slice.

## What it records

- **Three datasets, one per copyright class** (FRED's `cc` tag):
  `<instance>:fred_public` (public domain), `<instance>:fred_cited`
  (copyrighted, citation required), both pushed and pulled and kept; and
  `<instance>:fred_restricted` (pre-approval required), pulled only, served
  and never kept, three years of history. Each serves `Rate`; New York's
  day, ending at midnight; no calendar; no venue. A series whose class
  changes moves dataset.
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
`records-a-datasets-liveness` (it polls hourly and records no liveness).

## The terms, summarised

Not legal advice; read FRED's own words before relying on them.

- **FRED's API terms**: a free key; the notice "This product uses the FRED®
  API but is not endorsed or certified by the Federal Reserve Bank of St.
  Louis"; no replicating FRED's service.
- **Copyright is per series**, and a copyrighted series is its publisher's:
  beyond personal use, its owner's permission. Each class is its own dataset
  so each deployment's licence is one decision.

## Licence

Apache-2.0 (LICENSE, NOTICE). The responses under `src/fred/responses/` are
FRED's values, titles, update times and copyright tags as published on
2026-10-23, laid out as its API answers them (their `index.json` says how).
