# Setup

## Before launching

FRED's API needs a free key: sign in at
[fred.stlouisfed.org](https://fred.stlouisfed.org), open **My Account**, then
**API Keys**, and request one. Keep it to hand for Settings. Enter it there
yourself; an agent never types it.

Launch the plugin and approve its one role, `data` (a data plugin).

## Settings

In the dashboard's Settings form:

- **FRED API key**: your key, required. It is never shown again. Until it
  is set the plugin's status names it missing, the plugin asks FRED
  nothing, and Connection says **No key**.
- **Series kept current**: the series recorded as each is published, one
  per row, each picked from the series this version carries. Empty by
  default: every series here duplicates its publisher's own plugin, so keep
  current only those you want from FRED as well. Any series it carries is
  still fetched when a reader wants it.
- **Raw responses window** and **past the window** (the SDK's): how long
  FRED's answers are kept in the plugin's storage, ten years by default, and
  whether they are then archived, kept or deleted.
- **Sample data**, on a deployment installed for development only: FRED's
  answers recorded on 23 October 2026, committed with the plugin, in place
  of FRED. Runs without the key.

## Its datasets

On the deployment's **Data sources** page (deployment admins):

1. **License each dataset.** Each describes FRED's terms and its class's
   in words, and declares no licence:
   - `<instance>:fred_public` (public domain, a citation requested);
   - `<instance>:fred_cited` (copyrighted, citation required; beyond
     personal use, the publisher's permission);
   - `<instance>:fred_restricted` (pre-approval required): served when
     wanted, never kept, suits it without the publisher's permission. It
     holds the S&P 500, the Dow Jones Industrial Average and the NASDAQ
     Composite levels, whose publishers' permission is needed to reproduce
     them (the dataset's terms quote their notices).

   Set each licence, with a note saying why; until one is set, the lake
   keeps the rows and reads every use right restrictively. FRED's
   notice and the citation belong in the note until the licence carries
   them.
2. **Entitle** each plugin that reads rates or index levels.
3. **Priority:** put each publisher's own dataset (the New York Fed's,
   Treasury's, the ECB's, the Board's) first, and FRED's after it.

## The records

Each series is recorded against a reference rate, curve or index record,
found by its administrator's code. The platform seeds the rates and curves;
it does not seed the four index records (`spdji:SPX`, `spdji:DJI`,
`nasdaq:COMP`, `cboe:VIX`) yet. The Datasets page's **Records** shows each
one's record, or **not held** when your deployment does not have it yet; its
rates wait until it does.
