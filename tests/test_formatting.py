"""Tests for output formatting helpers."""

from mytruv_cli.commands.data import _fmt_dollar, _fmt_pct


def test_fmt_dollar() -> None:
    assert _fmt_dollar("1234.56") == "$1,234.56"
    assert _fmt_dollar("0") == "$0.00"
    assert _fmt_dollar("1000000") == "$1,000,000.00"


def test_fmt_dollar_none() -> None:
    assert _fmt_dollar(None) == ""
    assert _fmt_dollar("") == ""


def test_fmt_dollar_invalid() -> None:
    assert _fmt_dollar("not_a_number") == "not_a_number"


def test_fmt_pct() -> None:
    assert _fmt_pct("33.3") == "33.3%"
    assert _fmt_pct("100") == "100.0%"
    assert _fmt_pct("0.5") == "0.5%"


def test_fmt_pct_none() -> None:
    assert _fmt_pct(None) == ""
    assert _fmt_pct("") == ""


def test_fmt_pct_invalid() -> None:
    assert _fmt_pct("abc") == "abc"
