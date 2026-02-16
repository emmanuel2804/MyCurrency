import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import date
from apps.exchange.infrastructure.providers.currency_beacon import CurrencyBeaconProvider

@pytest.fixture
def provider():
    return CurrencyBeaconProvider()

@pytest.fixture
def mock_requests_get(mocker):
    return mocker.patch("requests.get")

def test_get_exchange_rate_data_success(provider, mock_requests_get):
    """
    Test that get_exchange_rate_data returns the correct Decimal value
    when the API call is successful using /historical endpoint.
    """
    mock_response = Mock()
    mock_response.json.return_value = {
        "meta": {"code": 200, "disclaimer": "Usage subject to terms: https://currencybeacon.com/terms"},
        "response": {
            "date": "2024-05-21",
            "base": "USD",
            "rates": {
                "GBP": 0.7854
            }
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    rate = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert rate == Decimal("0.7854")
    mock_requests_get.assert_called_once()

    # Verify URL contains historical endpoint and date parameter
    call_args = mock_requests_get.call_args
    url = call_args[0][0]
    assert "/historical" in url
    assert "date=2024-05-21" in url
    assert "base=USD" in url
    assert "symbols=GBP" in url

def test_get_exchange_rate_data_api_error(provider, mock_requests_get):
    """
    Test that get_exchange_rate_data returns None when the API call fails.
    """
    mock_requests_get.side_effect = Exception("API Error")

    rate = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert rate is None
    mock_requests_get.assert_called_once()

def test_get_exchange_rate_data_missing_key(provider, mock_requests_get):
    """
    Test that get_exchange_rate_data handles missing keys in response gracefully
    by raising/catching exception (KeyError would be caught by general Exception).
    """
    mock_response = Mock()
    mock_response.json.return_value = {
        "meta": {"code": 200},
        "response": {"rates": {}} # Missing the currency rate
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    rate = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert rate is None
