"""Tiered date parsing: strptime -> dateutil -> (optional) dateparser."""

import datetime

import pytest

from invoice2data.extract import _dates
from invoice2data.extract._dates import parse_date


pytestmark = pytest.mark.windows_strict


def test_partial_date_uses_current_year(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDateTime(datetime.datetime):
        current_year = 2025

        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> "FrozenDateTime":
            return cls(cls.current_year, 1, 1, tzinfo=tz)

    monkeypatch.setattr(datetime, "datetime", FrozenDateTime)
    assert parse_date("March 1") == FrozenDateTime(2025, 3, 1)
    FrozenDateTime.current_year = 2026
    assert parse_date("March 1") == FrozenDateTime(2026, 3, 1)


def test_relative_date_uses_current_base(monkeypatch: pytest.MonkeyPatch) -> None:
    dateparser = pytest.importorskip("dateparser.date")
    current_base = {"value": datetime.datetime(2025, 12, 31)}
    monkeypatch.setattr(
        _dates,
        "_date_data_parser",
        lambda languages: dateparser.DateDataParser(
            languages=list(languages), settings={"RELATIVE_BASE": current_base["value"]}
        ),
    )
    assert parse_date("today", (), ("en",)) == datetime.datetime(2025, 12, 31)
    current_base["value"] = datetime.datetime(2026, 1, 1)
    assert parse_date("today", (), ("en",)) == datetime.datetime(2026, 1, 1)


def test_strptime_tier_uses_template_format() -> None:
    assert parse_date("31/12/2017", ("%d/%m/%Y",)) == datetime.datetime(2017, 12, 31)


def test_dateutil_tier_parses_iso_without_a_format() -> None:
    assert parse_date("2017-12-31") == datetime.datetime(2017, 12, 31)


def test_dateparser_tier_handles_localized_month() -> None:
    pytest.importorskip("dateparser")
    result = parse_date("15 mai 2024", (), ("fr",))  # French month name
    assert result is not None
    assert (result.year, result.month, result.day) == (2024, 5, 15)


def test_dateparser_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate dateparser not being installed.
    monkeypatch.setattr(_dates, "_date_data_parser", lambda languages: None)

    # Localized month can't be parsed by strptime/dateutil -> None without dateparser.
    assert parse_date("15 mai 2024", (), ("fr",)) is None
    # Numeric / ISO dates still parse via the first two tiers.
    assert parse_date("31/12/2017", ("%d/%m/%Y",)) == datetime.datetime(2017, 12, 31)
    assert parse_date("2017-12-31") == datetime.datetime(2017, 12, 31)
