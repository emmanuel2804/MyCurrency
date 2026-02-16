import pytest
from decimal import Decimal
from datetime import date
from apps.exchange.infrastructure.providers.mock import MockProvider


@pytest.fixture
def provider():
    return MockProvider()


def test_get_exchange_rate_data_success(provider):
    """
    Test that MockProvider generates a valid rate for supported currency pairs.
    """
    rate = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))

    assert rate is not None
    assert isinstance(rate, Decimal)
    assert rate > 0
    # EUR/USD should be around 0.85 with ±2% variation
    assert Decimal("0.833") < rate < Decimal("0.867")


def test_get_exchange_rate_data_different_pairs(provider):
    """
    Test different currency pairs return different rates.
    """
    usd_eur = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))
    usd_gbp = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert usd_eur != usd_gbp


def test_get_exchange_rate_data_deterministic(provider):
    """
    Test that same inputs produce same output (deterministic based on date seed).
    """
    rate1 = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))
    rate2 = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))

    assert rate1 == rate2


def test_get_exchange_rate_data_different_dates(provider):
    """
    Test that different dates produce different rates (due to random variation).
    """
    rate1 = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))
    rate2 = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 22))

    # Should be different due to different random seed
    assert rate1 != rate2


def test_get_exchange_rate_data_unsupported_currency(provider):
    """
    Test that unsupported currency returns None.
    """
    rate = provider.get_exchange_rate_data("USD", "XXX", date(2024, 5, 21))

    assert rate is None


def test_get_exchange_rate_data_cross_rate(provider):
    """
    Test cross rate calculation (EUR to GBP).
    """
    rate = provider.get_exchange_rate_data("EUR", "GBP", date(2024, 5, 21))

    assert rate is not None
    assert isinstance(rate, Decimal)
    # GBP/EUR should be around 0.73/0.85 = 0.858 with variation
    assert Decimal("0.8") < rate < Decimal("0.9")


def test_get_exchange_rate_data_precision(provider):
    """
    Test that rates are rounded to 6 decimal places.
    """
    rate = provider.get_exchange_rate_data("USD", "EUR", date(2024, 5, 21))

    # Check that it has max 6 decimal places
    rate_str = str(rate)
    if "." in rate_str:
        decimal_places = len(rate_str.split(".")[1])
        assert decimal_places <= 6
