"""A reading plugin for the e2e, on the Python SDK: the deployment's view of
what this plugin recorded, as a `reporting` plugin entitled to its dataset
reads it (W10.6). Not the plugin, and never shipped: the e2e runs it from
this directory in the plugin's own image, which carries the SDK.

It answers its page as JSON, so the harness's runner can read it
(`page --instance reader --level read PATH`):

  /rates?subject=ID&date=D[&dataset=D]
      one read by business date: each rate's dataset, row key, version,
      business date, subject, kind, value and unit as text, tenor,
      convention, percentiles, volume and published time; and what the lake
      left unanswered, with why;
  /datasets
      the datasets it may read.

Standard library and the SDK only; every amount stays text, never a float.
"""

import asyncio
import http.server
import json
import threading
import urllib.parse

import meridian
from meridian import Interface, Page, SourceChoice
from meridian.operations import as_decimal, as_money
from meridian.plugin.v1 import operations_pb2 as ops
from meridian.roles import reporting
from meridian.roles.data import rates

PORT = 8088
LOOP = asyncio.new_event_loop()


def rate_json(rate):
    meta = rate.meta
    volume = as_money(rate.volume) if rate.HasField("volume") else None
    convention = rate.convention
    return {
        "dataset": meta.source.dataset,
        "row_key": meta.row_key,
        "version": meta.version,
        "business_date": meta.business_date,
        "subject": meta.subjects[0].entity_id if meta.subjects else "",
        "kind": ops.RateKind.Name(rate.kind),
        "value": str(as_decimal(rate.value.value)),
        "unit": ops.ValueUnit.Name(rate.value.unit),
        "index_base": rate.value.index_base,
        "tenor": rates.tenor_label(rate.tenor)
        if rate.HasField("tenor") and rate.tenor.unit
        else "",
        "convention": (
            f"{ops.DayCount.Name(convention.day_count)} {ops.Compounding.Name(convention.compounding)}"
            if rate.HasField("convention")
            else ""
        ),
        "percentiles": {str(p.percentile): str(as_decimal(p.value)) for p in rate.percentiles},
        "volume": f"{volume.amount} {volume.currency_code}" if volume else "",
        "published": [
            t.at_ns for t in meta.source_times if t.kind == ops.SOURCE_TIME_KIND_PUBLISHED
        ],
    }


class Reader(reporting.Role):
    """The stand-in's `reporting` role class (SDK 0.35: each role one class,
    its acts made through it): it reads rates and its datasets, and hears
    nothing."""

    async def rates(self, query):
        one = lambda name: query.get(name, [""])[0]  # noqa: E731
        asked = {"subjects": [meridian.SubjectRef(entity_id=s) for s in query.get("subject", [])]}
        if query.get("dataset"):
            asked["sources"] = SourceChoice(named=query["dataset"])
        if one("date"):
            asked["business_date"] = one("date")
        answer = await self.list_rates(**asked)
        return {
            "rates": [rate_json(r) for r in answer.rates],
            "unanswered": [
                {
                    "subject": u.subject.entity_id,
                    "dataset": u.dataset,
                    "reason": ops.UnansweredReason.Name(u.reason),
                }
                for u in answer.unanswered
            ],
        }

    async def answer(self, path, query):
        if path == "/rates":
            return await self.rates(query)
        if path == "/datasets":
            listed = await self.list_datasets()
            return {"datasets": [d.dataset for d in listed.datasets]}
        return {"page": "the e2e's reader"}


def serve(reader):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            future = asyncio.run_coroutine_threadsafe(
                reader.answer(parsed.path, urllib.parse.parse_qs(parsed.query)), LOOP
            )
            try:
                body, status = json.dumps(future.result(timeout=60), sort_keys=True), 200
            except Exception as failed:  # said on the page, for the run to quote
                body, status = json.dumps({"failed": f"{type(failed).__name__}: {failed}"}), 500
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


#: What the stand-in registers, its whole declaration (contract v25): the
#: e2e prints it with meridian-declaration and the harness holds the
#: stand-in's registration to it.
DECLARATION = meridian.Declaration(
    interface=Interface(PORT, "The e2e's reader", pages=[Page("/", "Rates", levels=["read"])])
)


def main():
    reader = Reader()
    threading.Thread(target=serve, args=(reader,), daemon=True).start()
    # SDK 0.35: its role class registered on one connection, until the
    # harness stops it. Contract v25: what the stand-in registers is its
    # declaration.
    LOOP.run_until_complete(meridian.run_async(declaration=DECLARATION, roles=[reader]))


if __name__ == "__main__":
    asyncio.set_event_loop(LOOP)
    main()
