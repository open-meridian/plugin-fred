# meridian-fred

FRED's interest-rate series as an Open Meridian data plugin, in Python on the
open-meridian SDK (0.33.1, contract v28). It runs beside a sidecar in a
Meridian deployment and puts the rate series it carries into the
deployment's lake as `Rate` rows, through the SDK's rates helpers
(`meridian.roles.data.rates`), each against the platform's seeded
referential record for it: the New York Fed's reference rates, the FOMC's
target range, €STR and Treasury's par curves. What it may publish and
subscribe to comes from its one role, `data`, declared in `pyproject.toml`,
once a deployment admin approves it. It is FRED's plugin in
meridian-design's `spec/a-public-rates-and-filings-data-plugin.md` (stage 1,
the rates slice; rulings 343 to 349 made it one plugin per publisher's feed).

## What it is

- `src/fred/api.py` asks FRED's API three kinds of request (a series'
  metadata, its tags, its observations over a range) as JSON, with the
  standard library, one at a time, at most one a second. The API key, a
  secret setting, is added only as a request is sent: never kept, logged,
  said or shown. `SyntheticApi` answers from the responses committed under
  `src/fred/responses/`.
- `src/fred/series.py` is the FRED-ID map (the spec's Q4): each series this
  version carries, its subject (the platform's seeded record, by its
  administrator's code as a source-scoped `symbol`), its kind, convention
  and tenor, and its companion percentile and volume series.
- `src/fred/classes.py` reads each series' copyright class from its `cc` tag
  and names its dataset: `fred_public`, `fred_cited`, `fred_restricted`
  (the spec's Q9).
- `src/fred/feed.py` keeps the `fred_series` setting's series and each
  standing want's current, hourly, reading observations only where FRED's
  `last_updated` moved; converts each observation to a `Rate` through
  `rates.Feed`; and answers the lake's wants or declines them per subject
  (W10.7), through the SDK's `meridian.roles.data.Wants`.
- `src/fred/raw.py` keeps every answer as received in the storage the
  deployment grants (but a restricted series' values), notes the answer
  each rate was first read from, and moves months past their window as the
  SDK's settings say.
- `src/fred/page.py`, `records.py` and `templates/` are the data role's two
  pages under Manage (spec/plugin-pages-follow-their-role), Connection and
  Datasets, each a read tool (`read_connection`, `read_datasets`) on the
  deployment's MCP answering the role's common fields,
  `meridian.roles.data`'s records extended with FRED's (Sources; Lag,
  Records, FRED series and Terms). The templates extend the role's and draw
  its content in its order and words, only so the page fits one screen:
  Datasets' sections as tabs (`?view=`). Connection extends the role's at
  its blocks alone. Never rename or reorder a common section, row, column
  or label.

## The rules it keeps

- **A data plugin shows no rate.** Its pages show its connection, its
  datasets and how its subjects resolve. A test holds every page to it.
- **The key is a secret.** Never in a page, a log line, an error, a raw
  record or a test; tests use recorded exchanges and a made-up key.
- **Exact decimals.** A value is a `Decimal` from FRED's text, never a
  `float`. A "." is no row, never a zero.
- **Every subject is a seeded record,** resolved by its administrator's
  code, and a miss reported; nothing minted, no FIGI guessed. A series whose
  subject the platform does not seed is not carried.
- **The publisher's own plugin is primary** (ruling 495): every series here
  duplicates one, recorded with the same kind, tenor and convention so the
  deployment's source priority chooses.
- **Every row names its raw record,** kept before anything is read from it,
  and the same rate always names the answer it was first read from.
- **A published time only where known:** FRED's `last_updated`, for a
  series' latest observation first read now; none otherwise.
- **Stateless.** A restart reads FRED again and the lake answers what it
  recorded before unchanged.
- **The responses committed** are FRED's own values, titles, update times
  and copyright tags, read from its keyless public downloads and laid out as
  the API answers (`src/fred/responses/index.json` says how); no API key is
  handled in building the plugin.
- **The suite.** `tests/test_suite.py` runs `meridian.suites.run("data", ...)`
  on the plugin's own conversion, and passes: the cases a rates-only plugin
  never presents are the SDK's `RATES_NOT_PRESENTED`, and four more are
  named with why. Never write a producer that invents what FRED does not
  state.
- **The rates slice only.** Macro series (Observation, Series) come with the
  series slice.

## Checking it locally

    make ci-local                     # lint, tests, plugin check, image, e2e: the pre-push gate
    make preview SHOTS=/tmp/shots     # each page in a browser with the kit, at 375, 582 and 1280 px, on its own and framed

`make e2e` runs the plugin on core's plugin harness beside a reading plugin
(`e2e/reader.py`), FRED's API unreachable (`e2e/hosts`), sample data on,
and compares the lake with `e2e/expected.lake`. Every gate runs in a
container: the host needs only Docker and Python 3 for the e2e's runner.

This file is for any coding agent working on the plugin, and is committed with
it for whoever works on it next. It is the canonical one: `CLAUDE.md` and the
`develop-live` skill lead Claude Code here rather than repeating it.
`.dockerignore` keeps all of them out of the image and the live instance.

## Checking it: `meridian plugin check`

Whatever in this file can be decided from the text is checked, not only
said: `meridian plugin check` holds the plugin to the rules every Meridian
plugin is built to (the template's
shape, `[tool.meridian]`, the kit linked and no raw colour, nothing from
another origin, settings declared rather than read from the environment, no
secret logged or put in a page, the deployment reached only through the SDK,
and tests). It needs no deployment and no session, and changes nothing. It
came in `meridian` 0.1.15; with an older one, the person runs
`meridian upgrade`.

- **Run `meridian plugin check` after each change.** Exit 0: every rule
  holds. Exit 1: at least one does not. Each failure names the rule, the file
  and line, and what to write instead: fix each one as it says, then run it
  again, until it exits 0. Never work around a rule; if one seems wrong for
  this plugin, tell the person.
- **`meridian plugin check --run-tests`** also runs the tests under `tests/`
  with pytest, in the plugin's `.venv` if it has one, otherwise with the
  `python3` on the PATH, which needs the plugin and pytest installed
  (`pip install -e . pytest`). `tests/test_page.py` asks the pages under
  Manage, Open and View with `meridian.testing.PageClient`, and the operation
  they send against a stand-in for the sidecar; replace its tests as you
  replace the pages, and add one for each page and each operation.
- The plugin's CI (`.github/workflows/check.yaml`) runs the same
  `meridian plugin check --run-tests` on every pull request and every push
  to main.
- **A change lands through a pull request** (CI-first): push a branch, open
  the pull request, and merge once its CI is green. The same pull request
  raises `version` in `pyproject.toml` and adds the change to `CHANGELOG.md`
  under a heading for that version, `## X.Y.Z`, with no date and no
  "(unreleased)": the date lives on the release tag and the listing. A
  version is never replaced. The pre-push hook (`hooks/pre-push`, activated
  once with `git config core.hooksPath hooks`) runs nothing for a branch push
  or a tag push, and runs `meridian plugin check --run-tests` before a push
  straight to main. Never bypass it with `--no-verify`.

What the check cannot decide stays advice, below: which component fits, the
page's layout, custom properties the kit does not define, figures as strings,
and names.

## Its declaration and its documentation

**The declaration is the whole of what a version says about itself**
(contract v25): `src/fred/declaration.py`'s `DECLARATION` --
its settings, its interface (its pages, and the tools their typed routes
make), whether it reads external accounts, and its documentation. `meridian
plugin upload` reads it from the built image, and the deployment holds the
running plugin to it: a version registering anything its upload did not
declare is refused, naming the difference. So:

- declare everything in `Declaration(...)` and call
  `meridian.connect(declaration=DECLARATION)` alone;
- keep the interface's port fixed (`PORT`), never read from the
  environment;
- keep `declaration.py` importing every module that declares a page or a
  route, so its tools are all of them;
- a change to any of it is a new version, which a person approves.

**`docs/` is the documentation a deployment admin reads** on the plugin's
Documentation tab, before launching it, and an agent reads through the
deployment's tools. One Markdown file per section, each name fixed:

- `overview.md` (required): what the plugin does, for whom, and what it
  does not do;
- `setup.md` (required): what to arrange with the vendor first, and the
  steps after launching;
- `troubleshooting.md` (prompted): one heading per problem, in the words
  its Summary or pages show, and how a person puts it right;
- `terms.md` (prompted): the vendor's terms a deployment accepts by using
  it, linked, or that it calls no vendor;
- `pages.md` (optional): a sentence per page, who opens it and why.

Write them for the person reading, in plain words: headings, paragraphs,
lists, tables, links. No HTML and no images, which the tab never shows; at
most 64 KiB a section. Do not restate what the Reference beside them already
lists from the declaration (every setting, page and tool): say why, not
what. The text is shown as the vendor's words and screened, so write
nothing that addresses an agent or tells it to act, and claim no
endorsement, verification or regulatory readiness. Any other file in
`docs/` is the repository's own and is not uploaded. `meridian plugin
check` fails a plugin without `overview.md` or `setup.md`, or with a
section it cannot show safely, and advises on the rest.

## Building its pages: the kit

Build every page with Open Meridian's plugin UI kit, and nothing else for its
look. Then it looks like the rest of the platform, follows each person's
colour scheme, light or dark, and their market-direction convention, and
needs no design work. The kit is plain CSS and web components: it works from
plain HTML, as the templates write it, and from React, Vue or Svelte alike.

**It is linked for you.** Each page's template, under `templates/`, is a
Jinja2 template that extends the SDK's base template,
`{% extends "meridian/base.html" %}`, which links the kit from the path the
dashboard serves it at on this plugin's own host and draws the page's heading
and tab row (the kit drops both when the dashboard frames the page and draws
its own). A template fills three blocks: `content`, the page itself;
`head_actions`, buttons marked `data-om-action="<id>"`, which the dashboard
draws in its header; and `status`, an `<om-status data-om-header>` it draws
beside the plugin's name. `pages.render("x.html", ...)` renders it, every
value escaped, with `caller` and `level` (admin, write or read) in it; a
template adapts by `{% if level == "write" %}`, and `{% include %}` and
macros share pieces between pages. A form that posts puts `{{ csrf_input }}`
inside it (a script sends `request.csrf_token` as `X-CSRF-Token`): every
request but GET and HEAD without this plugin's token is refused before the
view runs, so another site's page cannot act here as the person. A GET
changes nothing.

Never copy the kit into the plugin, and never load it, or anything else for
the page, from another origin or a CDN.

**Which component for what:**

| For | Use |
|---|---|
| A table of records | `<om-grid row-key="…">`: set `columns`, then `setRows(rows)`; `upsert(rows)` replaces rows by key in place; figures sort exactly |
| A stream: thousands of rows, many changes a second | `<om-grid high-rate>`: only the rows in view are drawn, only changed cells are touched, and they flash up or down; `freeze-sort` stops rows jumping while streaming |
| Live data from the plugin's server | `<om-live src="events" snapshot="snapshot.json" for="grid-id">`: follows server-sent events in sequence, and reads the snapshot again after a gap or a reconnect, so nothing is missed |
| The date the figures are as of | `<om-asof>` |
| Choosing an instrument | `<om-instrument-picker src="…" asof="…">`, searching through the plugin's own server |
| A time series | `<om-chart type="line">` (or `bar`), `series` set in script |
| Several views on one page, resizable and rearrangeable | `<om-panels layout-id="…">`, a `data-panel` child per view; each person's arrangement is remembered |
| Everything else | The kit's classes: `.page`, `.page-head`, `.panel` and `.panel-body`, `.tiles`, `.tabs`, `.field`, `.filters`, `.notice`, `.badge`, `button.primary` and `.danger`, `table` and `.num`, `.empty-state` |

Give a component its data as JSON inside it, `<script
type="application/json">{{ grid | tojson }}</script>`, which needs no script of the
page's; or set it (`columns`, `rows`, `series`) as properties, in a
`customElements.whenDefined(...)` callback. The kit's README
(open-meridian/meridian-ui) documents every component, attribute and event.

**Colour.** Only the kit's custom properties, never a hex, `rgb()`, `hsl()` or
a colour's name: not in a stylesheet, an inline style, an SVG or a script. A
person chooses their scheme and their deployment's administrator may add
schemes; a raw colour is one no scheme can change and no contrast check has
seen. Prefer a class to a property, and a property to anything else:

- surfaces `--page`, `--card`, `--hover`; text `--ink`, `--ink-soft`,
  `--ink-faint`; edges `--line`, `--line-soft`, `--line-strong`
- `--accent` and `--accent-wash`; `--primary` and `--primary-ink`
- status, which never changes meaning: `--good`, `--danger`, `--warn-ink`,
  `--violet`, each with its `-wash`
- **market direction:** `--buy` for a buy, a rise or a gain, and `--sell` for a
  sell, a fall or a loss, with `--buy-wash` and `--sell-wash`. Never green and
  red, and never `--good` and `--danger`, for a price move: where a person
  reads red as up (China, Japan, Korea, Taiwan) the kit swaps buy and sell for
  them. In markup, `.buy-ink` and `.sell-ink`, `.badge.buy` and `.badge.sell`;
  in a grid, a column's `tone: "sign"`.

Spacing, radii, shadows and type are the kit's too: `var(--space-1)` to
`var(--space-10)`, `var(--radius)`, `var(--shadow)`, `var(--sans)`,
`var(--mono)`.

**No chrome, no theme code.** The dashboard frames the page and draws the
plugin's name, its tab row, the way back to the dashboard and the person. The
page draws only its content, which the base template puts inside `<main
class="page">`: no header bar, navigation, logo, sign-in or sign-out, and no
light and dark switch. The kit applies the
person's theme, which the frame hands it, with no code of the page's.

**Money is exact.** Send prices and quantities to the page as decimal strings
and show them as sent; never `parseFloat` one. The grid sorts them exactly.

**The kit's rules, which a page keeps too:** no raw colour; no custom
property the kit does not define, other than the page's own layout ones; the
page reaches only its own origin, the plugin's server, which proxies anything
further; figures are strings, never floats.

**Where the kit is not served.** Until every dashboard serves `/.meridian/ui/`,
build pages that work without it, as the templates do: put a plain `<table>`
inside `<om-grid>` (a browser shows it as it is, and the kit's grid replaces
it), give components their data as JSON inside them, and make actions plain
forms. Without the kit the page is unstyled, but everything on it works.

A short page, whole: the view, in `page.py`,

```python
COLUMNS = [
    {"key": "symbol", "label": "Instrument"},
    {"key": "quantity", "label": "Quantity", "type": "decimal", "group": True},
    {"key": "market_value", "label": "Market value", "type": "decimal", "group": True},
    {"key": "day_pnl", "label": "Day P&L", "type": "decimal", "group": True, "tone": "sign"},
]


@pages.page("/positions", "Positions", levels=["write", "read"])
def positions(request: meridian.Request) -> str:
    return pages.render("positions.html", grid={"columns": COLUMNS, "rows": []})
```

and its template, `templates/positions.html`:

```html+jinja
{% extends "meridian/base.html" %}
{% block head_actions %}
<om-live src="events" snapshot="positions.json" for="positions"></om-live>
{% endblock %}
{% block content %}
<p class="muted">Every account you may read here.</p>
<section class="panel">
  <om-grid id="positions" row-key="position_id" high-rate sort="market_value:desc" caption="Positions">
    <script type="application/json">{{ grid | tojson }}</script>
    <table><tr><th>Instrument</th><th>Quantity</th><th>Market value</th></tr></table>
  </om-grid>
</section>
{% endblock %}
```

The plugin's server answers `positions.json` with `{ "sequence": "41", "rows":
[…] }` and `events` as server-sent events, each `id: <sequence>` and `data:
{ "rows": […] }` carrying whole records; `om-live` feeds them to the grid.

## Developing it live

On a Meridian deployment installed for development, `meridian plugin dev`
runs this plugin as you write it: each saved file is sent, the plugin's process
restarts on it in the same pod, and it is running again in about a second. The
pod, its sidecar and what it is allowed to do stay as they were.

Everything here runs on the person's own session with the deployment, and is
theirs.

### Before starting

- `meridian --version` is 0.1.21 or later. Older ones have no `--level` on
  `plugin open`, before 0.1.15 no `plugin check`, and before 0.1.3 no
  `plugin dev`: the person runs `meridian upgrade`.
- The person has run `meridian connect` (with the address, for a deployment
  not on this machine). You cannot do it for them: it signs in through their
  browser. `meridian plugin list` says whether the
  session is there: it lists the catalogue, or exits **3**. Whenever any
  command exits 3, the session is missing or has lapsed. Stop, tell the person
  to run the `meridian connect` the command printed, and carry on once they
  have. There is no `meridian status`.
- The deployment was installed for development (`meridian up --development`).
  Elsewhere `plugin dev` is refused, and nothing is wrong with the plugin.

### Start the loop

The instance is called `fred` below. Use whatever the person
wants it called, and the same name in every command.

**The first time an instance is launched, the person approves what it asks
for.** Show them the `roles` in `pyproject.toml`'s `[tool.meridian]`
and ask. Only once they say yes, pass `--yes`; never pass it to get past a
question they have not answered. An instance that is live already asks
nothing.

Run it in the background, and keep it running for the whole session:

```sh
mkdir -p .meridian
meridian plugin dev --instance fred --yes --json > .meridian/dev.jsonl 2> .meridian/dev.err
```

Its output goes under `.meridian/` on purpose. `plugin dev` sends every file
in this directory that changes, except `.meridian/` and what `.dockerignore`
names. Anywhere else in this directory, its own output would be sent to the
plugin as a change, again and again. Not under your own agent's directory
(`.claude/`, `.cursor/` and the like) either: some agents guard theirs, and
writing there needs a permission a session may not have. `.meridian/` is
git-ignored, since it is this session's, not the plugin's.

`.meridian/dev.jsonl` gets one JSON object a line:

| `event` | Means |
|---|---|
| `seeded` | The live folder was filled from the plugin's image, the first time it runs live |
| `sent` | This process sent a change; `revision` is the number it was given |
| `synced` | The sidecar wrote it |
| `restarted` | The plugin's process started on that revision |
| `ready` | It connected to its sidecar again: that revision is running |
| `crashed` | It stopped with an error. `traceback` has the last of what it printed |
| `exited` | It stopped by itself, without an error |
| `refused` | The sidecar refused it something; `reason` says what |

Wait for the first `ready` before changing anything. `.meridian/dev.err` says
what it is doing, and why it stopped if it did. The first run builds and
uploads the plugin's image, which takes a minute or two.

### Change something

1. Edit and save. There is nothing to run: the save is the deploy.
2. Find the `sent` line after your save, and its `revision`, R.
3. Wait for `ready` or `crashed` at R. Nothing about R is known before then.
4. On `crashed`, read its `traceback`, fix the cause, and save again: the next
   revision replaces it. Nothing needs restarting.

Several saves close together can land as one revision. Read the newest `sent`.

### Check it

Ask the question that answers what you changed:

| To know | Run |
|---|---|
| What a page shows, as the person is served it | `meridian plugin open --instance fred --level open --print /` for Accounts under Open (`--level view` under View), and `--level manage --print /setup` for Setup under Manage: any path on the plugin, at a level it is declared with |
| What the plugin printed or logged since your change | `meridian plugin logs --instance fred --since <R-1>` |
| What the sidecar refused it, or what else happened | `meridian plugin events --instance fred --since <R-1> --json` |
| What the person sees in a browser | `meridian plugin open --instance fred --level open`: a link one browser opens once, at that level. Give it to the person, or open it in your browser pane |

`--level` is the home's button the session is opened by: `manage`, `open` or
`view`. Name it every time. A page answers 403 at a level it is not declared
with, and without `--level` the dashboard opens at the first level the person
holds, Manage before Open before View, so on a development deployment, where
they hold `admin`, `/` would be asked under Manage and refused.

`--print` exits non-zero when the plugin answers with an error, and prints what
it answered. Prefer it to a browser for checking your own work: it needs no
browser and gives the same page every time.

### What a save cannot change

- **What it is allowed to do.** A `refused` event is its grants working, not a
  bug to code around. Adding a role to `pyproject.toml` changes nothing
  live: it takes a new version, and a person approves it.
- **Its dependencies.** The live code runs on the image the instance was
  launched from. A new package in `pyproject.toml` needs a new version.

Tell the person when a change needs either, rather than looking for a way
round it.

### Release it

When the person is satisfied:

1. Run `meridian plugin check --run-tests`, and fix what fails until it
   exits 0.
2. Raise `version` in `pyproject.toml`. A version is never replaced.
3. Show the person the roles again, and get their yes.
4. Run `meridian plugin dev --release --instance fred --yes`.

That uploads this directory as that version and runs it in place of the live
instance. It is then an ordinary version in the deployment's catalogue.

### Stop

Stop the background `plugin dev`. The instance keeps running, live, as it was.
`meridian plugin stop fred` ends it, which is the person's call.

## Publish it to a registry

To list a version on the platform's registry, publish a signed release tag
of it:

1. Once: `meridian plugin key setup`. It makes git's SSH signing key ready,
   or a new one, sets git to sign tags with it, and registers its public half
   on the organisation. Somebody who is not the organisation's Owner or Admin
   is told to ask one, with the line to give them.
2. Then, once the change's pull request is merged and main's CI is green:
   `meridian plugin release X.Y.Z`, the version `pyproject.toml` and
   `CHANGELOG.md` already say. It checks the checkout is on main, clean and
   up to date; X.Y.Z is higher than the last release tag; `pyproject.toml`
   says X.Y.Z; `CHANGELOG.md` has its `## X.Y.Z` heading; and main's CI is
   green. Then it signs `vX.Y.Z` on main's head, pushes it, publishes it and
   follows the build until it is listed, queued for review, or refused. It
   opens no pull request and changes no file; each refusal says what to do
   next. It reads main's CI with the person's GitHub sign-in: `GH_TOKEN` or
   `GITHUB_TOKEN`, else the credential git keeps for github.com.
