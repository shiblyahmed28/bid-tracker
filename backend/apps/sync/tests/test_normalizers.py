import datetime
from decimal import Decimal

import pytest

from apps.sync.normalizers import (
    norm_date,
    norm_delivery_type,
    norm_enum,
    norm_money,
    norm_person,
    norm_text,
    norm_time,
)


class TestNormText:
    @pytest.mark.parametrize("value", [None, "", "-", "N/A", "NA", "n/a", "na", "  ", "-  "])
    def test_null_tokens_become_none(self, value):
        assert norm_text(value) is None

    def test_strips_and_collapses_whitespace(self):
        assert norm_text("Aminul Quader Khalili ") == "Aminul Quader Khalili"
        assert norm_text("  Multiple   spaces   here  ") == "Multiple spaces here"

    def test_passthrough_for_normal_text(self):
        assert norm_text("Grameenphone Ltd") == "Grameenphone Ltd"


class TestNormPerson:
    def test_matches_after_stripping_trailing_whitespace(self):
        assert norm_person("Aminul Quader Khalili ") == norm_person("Aminul Quader Khalili")
        assert norm_person("Aminul Quader Khalili ") == "Aminul Quader Khalili"

    def test_null_token(self):
        assert norm_person("N/A") is None


class TestNormDate:
    def test_rejects_year_outside_2000_2100(self):
        # Row 184 in the real sheet.
        assert norm_date("Wed, May 07, 0206") is None

    @pytest.mark.parametrize(
        "raw",
        [
            "Wed,May 07,2026",
            "Wed, May 07,2026",
        ],
    )
    def test_parses_listed_formats(self, raw):
        assert norm_date(raw) == datetime.date(2026, 5, 7)

    def test_parses_abbreviated_month_format(self):
        assert norm_date("Thu,Jan 05,2023") == datetime.date(2023, 1, 5)

    def test_parses_slash_format(self):
        assert norm_date("07/05/2026") == datetime.date(2026, 5, 7)

    def test_parses_iso_format(self):
        assert norm_date("2026-05-07") == datetime.date(2026, 5, 7)

    def test_null_tokens_and_garbage_return_none(self):
        assert norm_date("N/A") is None
        assert norm_date("") is None
        assert norm_date("not a date") is None

    def test_passes_through_native_date(self):
        d = datetime.date(2026, 5, 7)
        assert norm_date(d) == d

    def test_native_date_out_of_range_rejected(self):
        assert norm_date(datetime.date(206, 5, 7)) is None

    def test_passes_through_native_datetime(self):
        dt = datetime.datetime(2026, 5, 7, 10, 30)
        assert norm_date(dt) == datetime.date(2026, 5, 7)


class TestNormTime:
    def test_parses_24h(self):
        assert norm_time("14:30") == datetime.time(14, 30)

    def test_parses_12h_with_meridiem(self):
        assert norm_time("2:30 PM") == datetime.time(14, 30)

    def test_null_token(self):
        assert norm_time("N/A") is None
        assert norm_time("") is None

    def test_garbage_returns_none(self):
        assert norm_time("not a time") is None


class TestNormMoney:
    def test_usd_prefix(self):
        raw, amount, currency = norm_money("USD 250000")
        assert raw == "USD 250000"
        assert amount == Decimal("250000")
        assert currency == "USD"

    def test_dollar_sign(self):
        raw, amount, currency = norm_money("$50,000")
        assert amount == Decimal("50000")
        assert currency == "USD"

    def test_bangladeshi_grouping(self):
        raw, amount, currency = norm_money("9,20,000.00")
        assert raw == "9,20,000.00"
        assert amount == Decimal("920000.00")
        assert currency == "BDT"

    def test_plain_bdt_amount_defaults_currency(self):
        raw, amount, currency = norm_money("500000")
        assert amount == Decimal("500000")
        assert currency == "BDT"

    def test_blank_cell_is_fully_blank(self):
        raw, amount, currency = norm_money("")
        assert raw == ""
        assert amount is None
        assert currency == ""

    def test_none_is_fully_blank(self):
        raw, amount, currency = norm_money(None)
        assert raw == ""
        assert amount is None
        assert currency == ""

    def test_unparseable_text_keeps_raw_and_nulls_amount(self):
        raw, amount, currency = norm_money("TBD")
        assert raw == "TBD"
        assert amount is None
        # Still benign, not quarantined — caller decides that, this just returns null.

    def test_never_raises_on_garbage(self):
        norm_money("!!!not-a-number###")
        norm_money("....")


class TestNormEnum:
    def test_uppercases_and_trims(self):
        assert norm_enum("  tender  ") == "TENDER"

    def test_null_token(self):
        assert norm_enum("N/A") is None

    def test_accepts_unknown_values(self):
        # §8: unfamiliar enum values are accepted and flagged for review, not rejected.
        assert norm_enum("Some New Stage") == "SOME NEW STAGE"


class TestNormDeliveryType:
    def test_services_singularizes_to_service(self):
        goods, works, service = norm_delivery_type("", "", "services")
        assert (goods, works, service) == (False, False, True)

    def test_all_three_present(self):
        goods, works, service = norm_delivery_type("goods", "works", "service")
        assert (goods, works, service) == (True, True, True)

    def test_na_and_blank_are_false(self):
        goods, works, service = norm_delivery_type("n/a", "", "N/A")
        assert (goods, works, service) == (False, False, False)

    def test_case_insensitive(self):
        goods, works, service = norm_delivery_type("Goods", "WORKS", "Service")
        assert (goods, works, service) == (True, True, True)
