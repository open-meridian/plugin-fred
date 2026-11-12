# Changelog

## 0.4.0

On open-meridian 0.36.0, contract 30, on core aae501d's harness (contract v30,
chart 0.1.538).

- **FRED's terms in words, by class** (ruling 1032): `licence_default` is
  gone from the contract. `meridian plugin migrate --to 0.36.0` could not
  read the licences (module-level names handed through `_dataset`), so they
  were written by hand: each dataset describes FRED's API terms (free key;
  the not-endorsed notice; no replicating FRED's service) and its copyright
  class's (`declared.TERMS`): public domain, a citation requested;
  copyrighted, citation required, the owner's permission beyond personal
  use; pre-approval, the owner's permission to reproduce. The Datasets page
  draws each class's own words in place of its fixed defaults. The plugin
  declares no licence: until a deployment admin sets one on Data sources,
  the lake keeps the rows and reads every use right restrictively --
  `fred_restricted` was served, never kept, by default, and is now the
  admin's to license so.
- **Datasets' Served table** shows each dataset's licence in its row and its
  terms in words in the row's details ("Terms and pricing"), so each row
  stays one line at 375 px.
- **How a gap is recovered** (W10.14): all three `backfill` -- FRED serves
  each series' history. No sessions calendar, no `most_shards`.
- **Pins**: open-meridian 0.36.0 and its base by digest; meridian 0.1.60 in
  the check workflow; core's runtime and harness at `aae501d`, by digest.

## 0.3.0

On open-meridian 0.35.2, contract v29 (rulings 1001 to 1005 and 1009 to 1023:
each role one class), on core v29's harness.

- **Each role one class:** `Feed` is the data role's class
  (`meridian.roles.data.Role`), its acts made on itself, and the SDK's
  `Wants`, `rates.Feed` and `Latency` given it (ruling 1023). `__main__`'s
  `Lake` registers it with `meridian.run`, which delivers the settings to
  `on_settings` before anything is heard, hands it the lake's wants, serves
  the pages and sets the figures; its hourly check, tending, the licences'
  read and the feed delay's report are its `run`, started again after a
  backoff should it fail. The hand-wired tasks and signal handling are gone.
- **The settings, typed:** `on_settings` receives the declared class, whose
  `.values` (open-meridian 0.35.2) holds the storage kind's window settings
  beside its fields, read as before.
- **Tests and preview:** the feed bound to the suite's `Recorder`
  (`recorder.bind`), what it hears handed by `recorder.hear`.
- **e2e:** the reader is a `reporting` role class run with
  `meridian.run_async`.
- **The pins:** open-meridian 0.35.2 and plugin-python:0.35.2 by tag and
  digest (`meridian plugin migrate --to 0.35.1`, then `--to 0.35.2`); core v29's runtime and
  harness at `1ae36f0` (chart 0.1.339) by digest; `meridian` 0.1.57 in
  check.yaml (was 0.1.52).

## 0.2.1

SDK 0.33.4: raw-record writes and enum conversion fixes (ruling 937).

- **The pins:** open-meridian 0.33.1 to 0.33.4, and plugin-python:0.33.4 by
  tag and digest (`meridian plugin migrate --to 0.33.4`: only the pins move),
  and the pin README.md states beside them.

## 0.2.0

On open-meridian 0.33.1, contract v28 (plugin-common-v28), on core v28's
harness.

- **The feed delay, reported** (ruling 518, required again from contract
  v28): each rate recorded unasked or for a standing want has its age at
  the edge recorded where it states a published time (`roles.Latency` on
  the SDK's `Wants`), reported every 10 seconds (`ReportLatency`);
  `reports-its-feed-delay` is presented on SOFR kept current.
- **The suite's v28 cases:** option chains, filings and the quality of
  quotes not presented, the SDK's `RATES_NOT_PRESENTED`.
- **`meridian plugin migrate`** (to_0_33_0, to_0_33_1): e2e/reader.py's
  SubjectRefs are `meridian.SubjectRef` (ruling 599).
- **The pins:** open-meridian 0.33.1 and plugin-python:0.33.1 by tag and
  digest; core v28's runtime and harness at `8def82a` (chart 0.1.313) by
  digest; `meridian` 0.1.52 in check.yaml (was 0.1.51).
- The README's "not released yet" is gone.

## 0.1.0

The first version: FRED's plugin with the lake's rates slice, on
open-meridian 0.32.2 (contract v27).

- **FRED's rate series as rates**, through the SDK's rates helpers: the New
  York Fed's SOFR, EFFR and OBFR (with percentiles and volume), the SOFR
  averages and SOFR Index; the FOMC target range's bounds; €STR (with
  volume); and Treasury's nominal and real par curves from H.15's
  constant-maturity series, each point against the curve's one record with
  its tenor. Each against the platform's seeded referential record.
- **Three datasets by copyright class**, `fred_public`, `fred_cited` and
  `fred_restricted` (pulled only, never kept); a series whose class changes
  moves dataset.
- **Settings:** the FRED API key, a secret; the series kept current, a typed
  table of the series carried; sample data.
- **Raw answers kept from the first day**, in the storage the deployment
  grants, the key never among them.
- **The data role's pages**, Connection (with Sources) and Datasets (its
  sections as tabs: Served with Lag, Wants, Records, FRED series and Terms),
  each a read tool on the deployment's MCP, each fitting one screen at 375,
  582 and 1280 px, on its own and in the dashboard's frame.
- **The data suite passes**: the rates slice's cases presented, but
  `two-conventions-one-tenor`.
- **The e2e** on core v27's plugin harness: each seeded referential record
  resolved by its administrator's code, rates recorded, read back by a
  reading plugin and wanted, the lake as expected.
