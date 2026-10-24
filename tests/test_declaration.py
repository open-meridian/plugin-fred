"""The catalogue, from code, as the deployment approves it."""

from __future__ import annotations

from meridian.plugin.v1 import operations_pb2 as ops

from fred.declaration import DECLARATION


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


def test_each_classes_terms() -> None:
    held = {d.key: d.licence_default for d in DECLARATION.catalogue}
    for key in ("fred_public", "fred_cited"):
        licence = held[key]
        assert licence is not None and licence.kept and licence.display
        assert licence.derived_use_terms == "not_restricted" and not licence.personal_use
    restricted = held["fred_restricted"]
    assert restricted is not None and not restricted.kept and restricted.display
    assert restricted.derived_use_terms == "internal_only" and not restricted.derived_use
    # The attribution fields are held until core accepts them (2026-10-24).
    for licence in held.values():
        assert licence is not None and not licence.attribution_text and not licence.copyright_class


def test_the_answers_are_kept_in_storage() -> None:
    assert DECLARATION.storage is not None
    assert [k.name for k in DECLARATION.storage.kinds] == ["responses"]
