# Setup

## Before launching

FRED's API needs a free key: sign in at
[fred.stlouisfed.org](https://fred.stlouisfed.org), open **My Account**, then
**API Keys**, and request one. Keep it to hand for Settings. Enter it there
yourself; an agent never types it.

Launch the plugin and approve its one role, `data` (a data plugin).

## Settings

In the dashboard's Settings form:

- **FRED API key**: your key. It is never shown again. Without it the
  plugin asks FRED nothing, and Connection says **No key**.
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
  of FRED. No key needed.

## Its datasets

On the deployment's **Data sources** page (deployment admins):

1. **License each dataset.** Each class has its own defaults:
   - `<instance>:fred_public` (public domain): kept, derived use and
     display;
   - `<instance>:fred_cited` (copyrighted, citation required): kept, derived
     use and display, citing each series' source;
   - `<instance>:fred_restricted` (pre-approval required): served when
     wanted, never kept. This version carries no series of this class, but a
     series that FRED reclassifies moves here.

   Confirm each default or set your own, with a note saying why. FRED's
   notice and the citation belong in the note until the licence carries
   them.
2. **Entitle** each plugin that reads rates.
3. **Priority:** put each publisher's own dataset (the New York Fed's,
   Treasury's, the ECB's, the Board's) first, and FRED's after it.

## The records

Each series is recorded against a reference rate or curve the platform seeds,
found by its administrator's code. The Datasets page's **Records** shows each
one's record, or **not held** when your deployment does not have it yet; its
rates wait until it does.
