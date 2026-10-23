"""The settings as declared, in the data role's order, and read back."""

from __future__ import annotations

from meridian._settings import declared_by

from fred.series import CARRIED
from fred.settings import DECLARED, config_from


def test_declared_in_the_roles_order() -> None:
    declared = declared_by(DECLARED)
    assert [s.name for s in declared] == ["fred_api_key", "fred_series", "sample_data"]
    key, series, sample = declared
    assert key.secret and not key.required and key.label == "FRED API key"
    assert series.kind is list and [c.name for c in series.columns] == ["series"]
    column = series.columns[0]
    assert column.kind == "choice" and column.required
    assert [c.value for c in column.choices] == [s.series_id for s in CARRIED]
    assert sample.developer


def test_read_back() -> None:
    config = config_from(
        {
            "fred_api_key": " k3y ",
            "fred_series": [{"series": "dgs10"}, {"series": "SOFR"}, {"series": "DGS10"},
                            {"series": "BAMLH0A0HYM2"}, {"other": "x"}],
            "responses_window_days": 30,
            "responses_past_window": "archived",
        }
    )  # fmt: skip
    assert config.key == "k3y" and config.series == ("DGS10", "SOFR")
    assert config.window_days == 30 and config.past_window == "archived"
    assert not config.sample_data
    # The key is never in the configuration's repr.
    assert "k3y" not in repr(config)
    empty = config_from({})
    assert empty.key == "" and empty.series == () and empty.window_days == 3650
