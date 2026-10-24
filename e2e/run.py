"""`make e2e`: the plugin on the plugin harness of the runtime it pins
(contract v27, core a5da59a), beside `reader`, a reporting plugin
(e2e/reader.py) entitled to its datasets, and the harness's admin. Run from
the repository's root by the Makefile, which builds the image and writes the
harness's plugins first; standard library only.

The harness's platform holds the 28 referential records the platform seeds,
each named by its administrator's code as a `symbol` at its administrator
(nyfed, frb, ecb, ustreasury): FRED is not an administrator, so the plugin
names each record by its administrator's code, and the deployment resolves
it to the platform's `INS-` record (rulings 545, 547).

1. No key: Connection says "No key"; nothing is asked of FRED (whose API
   answers nowhere here, e2e/hosts) and nothing is recorded.
2. Sample data on, and seven series kept current (`fred_series`): SOFR,
   SOFRINDEX, DFEDTARL, DFEDTARU, ECBESTRVOLWGTTRMDMNRT, DGS10 and DGS30. The
   committed answers' last ten days, 12 to 22 October 2026, are recorded:
   61 rates, each against the `INS-` record its administrator's code
   resolved to -- the 10 and 30-year points against Treasury's par curve's
   one record.
3. Parity: through the deployment's MCP, `read_connection` and
   `read_datasets` answer what the pages show, under the data role's names
   -- the key not set, never a value; each record's `INS-` ID -- and core's
   `dashboard__list_datasets` lists the three datasets as the catalogue
   declares them.
4. Licensed and entitled at the Data sources page: the reader, to
   fred_public and fred_cited.
5. Read back: SOFR on 22 October from fred_cited, a fixing of 3.90 per cent,
   act/360 simple, with its percentiles, its volume in dollars and FRED's
   update time as its published time; Treasury's 10-year on 21 October from
   fred_public, the par curve's record with tenor 10Y, 5.13 per cent.
6. Wanted: SOFR on 24 September, not recorded, is asked of the plugin, which
   reads it from FRED and records it against the want (3.88); Columbus Day,
   12 October, which FRED states as ".", is declined `source_silent`; and
   TGCR, a seeded record FRED carries no series of, `not_covered`.
7. `store lake` is e2e/expected.lake.
8. A new container: it reads the series again and records nothing twice;
   the lake is unchanged, and it reads its datasets' licences on start.
"""

import json
import os
import subprocess
import sys
import time

PROJECT = "fred-e2e"
LOG = ".e2e/runner.log"
COMPONENTS = ".e2e/components.log"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    PROJECT,
    "-f",
    ".e2e/harness/compose.yaml",
    "-f",
    ".e2e/harness/plugins.yaml",
    "-f",
    "e2e/plugin.yaml",
]
PUBLIC, CITED, RESTRICTED = "fred:fred_public", "fred:fred_cited", "fred:fred_restricted"
KEPT = ["SOFR", "SOFRINDEX", "DFEDTARL", "DFEDTARU", "ECBESTRVOLWGTTRMDMNRT", "DGS10", "DGS30"]
#: The rates the seven series' last ten days hold, FRED's "." days left out.
CURRENT = 61
#: TGCR's record in the harness's platform: the fourth it seeds
#: (platform.py, REFERENTIAL_SEEDS), a record FRED carries no series of.
TGCR = f"INS-01JREF{4:020d}"
#: SOFR's last_updated in the committed answers, 2026-10-23 07:02 Central.
SOFR_PUBLISHED = 1792756920 * 10**9


class Failed(Exception):
    pass


def log(text):
    with open(LOG, "a", encoding="utf-8") as kept:
        kept.write(text + "\n")


def compose(*args, check=True, timeout=600):
    done = subprocess.run(COMPOSE + list(args), capture_output=True, text=True, timeout=timeout)
    log(f"$ compose {' '.join(args)[:300]}\n{done.stdout[-4000:]}{done.stderr[-2000:]}")
    if check and done.returncode != 0:
        raise Failed(
            f"compose {' '.join(args)[:200]}: {(done.stdout + done.stderr).strip()[-600:]}"
        )
    return done


def runner(*args, check=True):
    done = compose("run", "--rm", "-T", "runner", *args, check=check)
    return done.stdout if check else done


def must(condition, why):
    if not condition:
        raise Failed(why)


def until(seconds, attempt, what):
    deadline = time.monotonic() + seconds
    last = None
    while True:
        try:
            answer = attempt()
        except Failed as failed:
            answer, last = None, failed
        if answer:
            return answer
        if time.monotonic() > deadline:
            raise Failed(f"{what}, in {seconds} seconds" + (f": {last}" if last else ""))
        time.sleep(2)


def page(instance, level, path):
    said = runner("page", "--instance", instance, "--level", level, path)
    status, _, body = said.partition("\n")
    must(status.strip() == "200", f"{instance} {path} answered {said[-600:]}")
    return body


def rates(subject, day, dataset):
    """The reader's read of one of the plugin's datasets, by business date."""
    return json.loads(
        page("reader", "read", f"/rates?subject={subject}&date={day}&dataset={dataset}")
    )


def call(tool, arguments=None):
    done = runner("mcp", "call", tool, json.dumps(arguments or {}), check=False)
    try:
        answer = json.loads(done.stdout)
    except ValueError:
        raise Failed(f"{tool}: no answer: {(done.stdout + done.stderr)[-400:]}")
    must(answer.get("outcome") in ("read", "unchanged"), f"{tool} answered {done.stdout[-700:]}")
    return answer["data"]


def store_lake():
    return compose("run", "--rm", "-T", "store", "lake").stdout


def sorted_lines(lines):
    return "\n".join(sorted(lines.strip().splitlines())) + "\n"


def run():
    started = time.time()
    compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
    compose("up", "-d")
    runner("ready")
    runner("ready", "--instance", "reader")
    # The conductor pulls the platform's licence list on start and hands it
    # to the instrument store on the bus; started together, the store may
    # not be listening yet, and until the next (daily) pull it sends by the
    # open schemes, which hold no administrator_symbol. Started again once
    # the store serves, its pull reaches the store.
    compose("restart", "conductor")
    time.sleep(5)

    # 1. No key: nothing asked, nothing recorded.
    runner("page", "--level", "admin", "/", "--until", "No key yet", "--seconds", "90")
    lake = store_lake()
    must("row|" not in lake, f"step 1, nothing recorded without a key: {lake}")

    # 2. Sample data, and seven series kept current.
    rows = [f"fred_series[{n}].series={s}" for n, s in enumerate(KEPT)]
    runner("settings", "sample_data=true", *rows)
    until(
        120,
        lambda: store_lake().count("row|") >= CURRENT,
        f"step 2, the {CURRENT} current rates were not recorded",
    )
    runner(
        "page",
        "--level",
        "admin",
        "/datasets?view=records",
        "--until",
        "INS-01JREF",
        "--seconds",
        "60",
    )

    # 3. Parity through the deployment's MCP, and core's view of the catalogue.
    runner("grant", "--level", "admin")
    runner("mcp", "connect", "--covers", "deployment_admin", "--covers", "fred:admin")
    tools = runner("mcp", "list").split()
    read_connection = next((t for t in tools if t.endswith("read_connection")), "")
    read_datasets = next((t for t in tools if t.endswith("read_datasets")), "")
    must(read_connection and read_datasets, f"step 3, the plugin's two tools are listed: {tools}")
    connection = call(read_connection)
    must(
        connection["mode"] == "Sample data"
        and connection["credentials"] == [{"label": "FRED API key", "set": False}]
        and connection["kept_current"] == len(KEPT)
        and connection["sessions"] is None,
        f"step 3, read_connection: {connection}",
    )
    datasets = call(read_datasets)
    ids = {r["name"]: r["instrument_id"] for r in datasets["records"]}
    sofr, par = ids["nyfed:SOFR"], ids["ustreasury:Daily Treasury Par Yield Curve Rates"]
    for name in (
        "nyfed:SOFR",
        "nyfed:SOFR Index",
        "frb:FOMC target range lower bound",
        "frb:FOMC target range upper bound",
        "ecb:ESTR",
        "ustreasury:Daily Treasury Par Yield Curve Rates",
    ):
        must(
            ids.get(name, "").startswith("INS-"),
            f"step 3, {name} resolved by its administrator's code to an INS- record: {ids}",
        )
    shown = page("fred", "admin", "/datasets?view=records")
    must(
        all(i in shown for i in ids.values() if i),
        "step 3, Records shows what read_datasets answers",
    )
    must(
        [s["dataset"] for s in datasets["served"]] == [PUBLIC, CITED, RESTRICTED],
        f"step 3, read_datasets serves the three datasets: {datasets['served']}",
    )
    listed = {d["dataset"]: d for d in call("dashboard__list_datasets")["datasets"]}
    for name, modes in (
        (PUBLIC, ["push", "pull"]),
        (CITED, ["push", "pull"]),
        (RESTRICTED, ["pull"]),
    ):
        entry = listed.get(name, {}).get("catalogue_entry", {})
        must(
            entry.get("modes") == modes
            and entry.get("day_time_zone") == "America/New_York"
            and entry.get("cadence") == 86400
            and not entry.get("calendar_id"),
            f"step 3, core lists {name} as declared: {listed.get(name)}",
        )

    # 4. Licensed and entitled.
    runner(
        "licence",
        PUBLIC,
        "kept=true",
        "retention_days=0",
        "derived_use=true",
        "display=true",
        "personal_use=false",
        "note=FRED's public-domain rate series, cited.",
    )
    runner(
        "licence",
        CITED,
        "kept=true",
        "retention_days=0",
        "derived_use=true",
        "display=true",
        "personal_use=false",
        "note=FRED's copyrighted rate series, each publisher cited.",
    )
    for name in (PUBLIC, CITED):
        runner("entitle", "--instance", "reader", name, "note=The e2e's reader reads the rates.")
    runner("grant", "--instance", "reader", "--level", "read")

    # 5. Read back.
    read = until(
        60,
        lambda: (lambda r: r if r["rates"] else None)(rates(sofr, "2026-10-22", CITED)),
        "step 5, SOFR on 22 October was not read",
    )
    [fixing] = read["rates"]
    must(
        fixing["value"] == "3.90"
        and fixing["unit"] == "VALUE_UNIT_PERCENT"
        and fixing["kind"] == "RATE_KIND_FIXING"
        and fixing["subject"] == sofr
        and fixing["convention"] == "DAY_COUNT_ACT_360 COMPOUNDING_SIMPLE"
        and fixing["percentiles"] == {"1": "3.83", "25": "3.88", "75": "3.95", "99": "3.98"}
        and fixing["volume"] == "2945000000000 USD"
        and fixing["version"] == 1
        and fixing["published"] == [SOFR_PUBLISHED]
        and fixing["dataset"] == CITED,
        f"step 5, SOFR as FRED states it: {fixing}",
    )
    curve = rates(par, "2026-10-21", PUBLIC)["rates"]
    ten = [r for r in curve if r["tenor"] == "10Y"]
    must(
        ten
        and ten[0]["value"] == "5.13"
        and ten[0]["kind"] == "RATE_KIND_PAR_YIELD"
        and {r["tenor"] for r in curve} == {"10Y", "30Y"},
        f"step 5, Treasury's 10 and 30-year points from H.15's series: {curve}",
    )

    # 6. Wants: a past day recorded against one; a holiday and a record it
    # carries no series of declined.
    rates(sofr, "2026-09-24", CITED)
    # Read again only once the plugin answered the want, so the lake asks once.
    until(90, lambda: f"want|{CITED}|answered|{sofr}|" in store_lake(),
          "step 6, the want for SOFR on 24 September was not answered")
    past = until(
        90,
        lambda: (lambda r: r if r["rates"] else None)(rates(sofr, "2026-09-24", CITED)),
        "step 6, SOFR on 24 September was not recorded against the want",
    )
    must(past["rates"][0]["value"] == "3.88", f"step 6, SOFR on 24 September: {past}")
    rates(sofr, "2026-10-12", CITED)
    rates(TGCR, "2026-10-21", CITED)
    until(
        90,
        lambda: store_lake().count("|declined|") >= 2,
        "step 6, Columbus Day and TGCR were not declined",
    )
    lake = store_lake()
    must(
        f"want|{CITED}|declined|{sofr}|" in lake and f"want|{CITED}|declined|{TGCR}|" in lake,
        f"step 6, the declines name SOFR and TGCR: {lake[-1500:]}",
    )

    # 7. The lake.
    got = sorted_lines(store_lake())
    with open(".e2e/lake", "w", encoding="utf-8") as kept:
        kept.write(got)
    with open("e2e/expected.lake", encoding="utf-8") as held:
        expected = held.read()
    if got != expected:
        diff = subprocess.run(
            ["diff", "-u", "e2e/expected.lake", ".e2e/lake"], capture_output=True, text=True
        )
        raise Failed(f"step 7, the lake is not e2e/expected.lake:\n{diff.stdout[-3000:]}")

    # 8. A new container records nothing twice.
    compose("up", "-d", "--no-deps", "--force-recreate", "fred")
    runner("ready")
    until(
        120,
        lambda: "Thu 22 Oct 2026" in page("fred", "admin", "/"),
        "step 8, the new container did not read the series again",
    )
    time.sleep(5)
    again = sorted_lines(store_lake())
    must(
        again == got,
        "step 8, the new container recorded something twice:\n"
        + subprocess.run(
            ["diff", "-u", "-", ".e2e/lake"], input=again, capture_output=True, text=True
        ).stdout[-2000:],
    )
    logs = compose("logs", "--no-color", "fred").stdout
    must(
        f"0 recorded, 0 restated, {CURRENT} unchanged" in logs,
        "step 8, the new container's check was answered unchanged: " + logs[-800:],
    )
    until(
        90,
        # The two licensed here; the deployment answers each declared dataset
        # it holds a licence for, the restricted one's default among them.
        lambda: all(s["licensed"] for s in call(read_datasets)["served"][:2]),
        "step 8, the new container never read its datasets' licences",
    )

    print(
        f"e2e OK in {int(time.time() - started)}s on the plugin harness: with no key nothing asked "
        f"or recorded; sample data and seven series kept current recorded {CURRENT} rates, each "
        f"against the INS- record its administrator's code resolved to; read_connection and "
        f"read_datasets answering what the pages show, and core listing the three datasets as "
        f"declared; licensed and entitled; SOFR read back as FRED states it (3.90, its percentiles, "
        f"volume and published time) and Treasury's 10-year against the par curve; 24 September "
        f"wanted and recorded, Columbus Day declined source silent and TGCR not covered; `store "
        f"lake` as e2e/expected.lake ({got.count('row|')} rows); and a new container recording "
        f"nothing twice, its licences read on start"
    )


def main():
    os.makedirs(".e2e", exist_ok=True)
    open(LOG, "w").close()
    try:
        run()
    except (
        Failed,
        subprocess.TimeoutExpired,
        KeyError,
        ValueError,
        IndexError,
        TypeError,
    ) as failed:
        with open(COMPONENTS, "a", encoding="utf-8") as kept:
            kept.write(compose("logs", "--no-color", check=False).stdout)
        compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
        print(
            f"e2e FAILED: {failed}; the runner's log is in {LOG}, the components' in {COMPONENTS}",
            file=sys.stderr,
        )
        return 1
    compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
