"""The catalogue, from code, as the deployment approves it."""

from __future__ import annotations

from meridian.plugin.v1 import operations_pb2 as ops

from fred.declaration import DECLARATION
from fred.declared import FRED_TERMS, TERMS


def test_three_datasets_of_rates_one_per_class() -> None:
    held = {d.key: d for d in DECLARATION.catalogue}
    assert list(held) == ["fred_public", "fred_cited", "fred_restricted"]
    for dataset in held.values():
        assert list(dataset.data_types) == ["meridian.v1.Rate"]
        assert dataset.vendor == "Each series' publisher, as FRED states it"
        assert dataset.aggregator == "FRED, Federal Reserve Bank of St. Louis"
        assert dataset.day_time_zone == "America/New_York" and dataset.day_end_minute == 0
        assert dataset.cadence == 86_400 and not dataset.calendar_id and not dataset.venue_id
    modes = {k: [ops.ObservationMode.Name(m) for m in d.modes] for k, d in held.items()}
    assert modes["fred_public"] == modes["fred_cited"] == [
        "OBSERVATION_MODE_PUSH", "OBSERVATION_MODE_PULL"
    ]  # fmt: skip
    assert modes["fred_restricted"] == ["OBSERVATION_MODE_PULL"]
    assert held["fred_public"].history == 0 and held["fred_restricted"].history == 1095


def test_each_classes_terms_in_words_and_a_gap_asked_again() -> None:
    # Contract 30 (ruling 1032): each class's terms described, no licence.
    held = {d.key: d for d in DECLARATION.catalogue}
    for key, dataset in held.items():
        said = dataset.terms_and_pricing
        assert said == TERMS[key] and said.startswith(FRED_TERMS) and len(said) <= 2000
        assert "not endorsed or certified" in said
        assert dataset.gap_recovery == "backfill" and not dataset.sessions_calendar_id
    assert "public domain" in TERMS["fred_public"]
    assert "require citation" in TERMS["fred_cited"]
    assert "pre-approval" in TERMS["fred_restricted"]


def test_the_answers_are_kept_in_storage() -> None:
    assert DECLARATION.storage is not None
    assert [k.name for k in DECLARATION.storage.kinds] == ["responses"]
