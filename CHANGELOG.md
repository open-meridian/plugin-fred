# Changelog

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
