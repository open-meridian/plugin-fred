# Changelog

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
