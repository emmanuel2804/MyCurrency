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
    when the API call is successful.
    """
    mock_response = Mock()
    mock_response.json.return_value = {
        "meta": {"code": 200, "disclaimer": "Usage subject to terms: https://currencybeacon.com/terms"},
        "response": {
            "timestamp": 1716298200,
            "date": "2024-05-21",
            "from": "USD",
            "to": "GBP",
            "amount": 1,
            "value": 0.7854
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    rate = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert rate == Decimal("0.7854")
    mock_requests_get.assert_called_once()
    # verify URL parameters if necessary

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
        "response": {} # Missing value
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    rate = provider.get_exchange_rate_data("USD", "GBP", date(2024, 5, 21))

    assert rate is None
