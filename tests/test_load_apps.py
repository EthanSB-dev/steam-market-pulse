import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "ingestion"))
from load_apps import parse_release_date


def test_parse_release_date_valid():
    details = {"release_date": {"date": "Jun 9, 2026"}}
    result = parse_release_date(details)
    assert result is not None
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 9


def test_parse_release_date_missing_key():
    assert parse_release_date({}) is None


def test_parse_release_date_coming_soon():
    details = {"release_date": {"date": "Coming soon"}}
    assert parse_release_date(details) is None