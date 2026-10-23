"""Each series' copyright class, and the dataset it is served under
(spec/a-public-rates-and-filings-data-plugin, Q9: one dataset per copyright
class; §7).

FRED states a series' copyright as one tag of the `cc` group (its series
tags, `/fred/series/tags`): "public domain: citation requested",
"copyrighted: citation required" or "copyrighted: pre-approval required".
Each class is one dataset, so a deployment's licence for each is one
answer:

- `public` -- `fred_public`, kept, derived use and display, with FRED's
  non-endorsement notice;
- `cited` -- `fred_cited`, the same, citing the series' source;
- `restricted` -- `fred_restricted`, served when wanted and never kept (ICE
  BofA's series among them: reproduction needs ICE's permission), with three
  years of history.

A series whose class changes moves dataset, and the Datasets page's "FRED
series" says when (Q9). A series whose tags state no class, or which were
not read, is recorded under none until they are.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PUBLIC, CITED, RESTRICTED = "public", "cited", "restricted"

#: Each class's tag, as FRED names it, and its words on the pages.
TAGS = {
    "public domain: citation requested": PUBLIC,
    "copyrighted: citation required": CITED,
    "copyrighted: pre-approval required": RESTRICTED,
}
SAID = {
    PUBLIC: "Public domain: citation requested",
    CITED: "Copyrighted: citation required",
    RESTRICTED: "Copyrighted: pre-approval required",
}
#: The class's dataset key (the spec's §3, its keys approved with the batch).
DATASETS = {PUBLIC: "fred_public", CITED: "fred_cited", RESTRICTED: "fred_restricted"}
#: The copyright group's id among FRED's tag groups.
GROUP = "cc"


def class_of(answer: Mapping[str, Any]) -> str:
    """A series' class from its tags answer: `public`, `cited` or
    `restricted`; empty where it states none this version reads. Two classes
    stated are read as the stricter."""
    found = {
        TAGS[str(tag.get("name", "")).strip().lower()]
        for tag in answer.get("tags", [])
        if isinstance(tag, Mapping)
        and tag.get("group_id") == GROUP
        and str(tag.get("name", "")).strip().lower() in TAGS
    }
    for strictest in (RESTRICTED, CITED, PUBLIC):
        if strictest in found:
            return strictest
    return ""


def dataset_of(copyright_class: str) -> str:
    """The dataset key a class is served under; empty for none."""
    return DATASETS.get(copyright_class, "")
