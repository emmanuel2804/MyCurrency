import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch

from rest_framework.test import APIClient
from rest_framework import status

from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
    ProviderName
)


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def currencies(db):
    """Create test currencies."""
    Currency.objects.all().delete()
    usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    gbp = Currency.objects.create(code="GBP", name="British Pound", symbol="£")
    return {"USD": usd, "EUR": eur, "GBP": gbp}


@pytest.fixture
def mock_provider_active(db):
    """Create active mock provider in DB."""
    Provider.objects.all().delete()
    return Provider.objects.create(
        name=ProviderName.MOCK,
        priority=1,
        is_active=True
    )


@pytest.mark.django_db(transaction=True)
class TestCurrencyViewSet:
    """Tests for CurrencyViewSet endpoints."""

    def setup_method(self):
        """Clean up before each test."""
        Currency.objects.all().delete()

    def test_list_currencies(self, api_client, currencies):
        """
        Test GET /api/v1/exchange/currencies/ lists all currencies.
        """
        response = api_client.get("/api/v1/exchange/currencies/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_retrieve_currency(self, api_client, currencies):
        """
        Test GET /api/v1/exchange/currencies/{id}/ retrieves a single currency.
        """
        currency_id = currencies["USD"].id
        response = api_client.get(f"/api/v1/exchange/currencies/{currency_id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == "USD"
        assert response.data["name"] == "US Dollar"

    def test_create_currency(self, api_client):
        """
        Test POST /api/v1/exchange/currencies/ creates a new currency.
        """
        data = {
            "code": "CHF",
            "name": "Swiss Franc",
            "symbol": "CHF"
        }
        response = api_client.post("/api/v1/exchange/currencies/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"] == "CHF"
        assert Currency.objects.filter(code="CHF").exists()

    def test_update_currency(self, api_client, currencies):
        """
        Test PUT /api/v1/exchange/currencies/{id}/ updates a currency.
        """
        currency_id = currencies["USD"].id
        data = {
            "code": "USD",
            "name": "United States Dollar",
            "symbol": "$"
        }
        response = api_client.put(f"/api/v1/exchange/currencies/{currency_id}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "United States Dollar"

    def test_delete_currency(self, api_client, currencies):
        """
        Test DELETE /api/v1/exchange/currencies/{id}/ deletes a currency.
        """
        currency_id = currencies["GBP"].id
        response = api_client.delete(f"/api/v1/exchange/currencies/{currency_id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Currency.objects.filter(id=currency_id).exists()


@pytest.mark.django_db(transaction=True)
class TestCurrencyExchangeRateViewSet:
    """Tests for CurrencyExchangeRateViewSet endpoints."""

    def setup_method(self):
        """Clean up before each test."""
        CurrencyExchangeRate.objects.all().delete()
        Currency.objects.all().delete()

    def test_list_rates(self, api_client, currencies):
        """
        Test GET /api/v1/exchange/rates/ lists all exchange rates.
        """
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.850000")
        )

        response = api_client.get("/api/v1/exchange/rates/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_retrieve_rate(self, api_client, currencies):
        """
        Test GET /api/v1/exchange/rates/{id}/ retrieves a single rate.
        """
        rate = CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.850000")
        )

        response = api_client.get(f"/api/v1/exchange/rates/{rate.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["source_currency"]["code"] == "USD"
        assert response.data["exchanged_currency"]["code"] == "EUR"

    def test_time_series_success(self, api_client, currencies):
        """
        Test GET /api/v1/exchange/rates/time-series/ returns rates within date range.
        """
        # Create rates for different dates
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.850000")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 22),
            rate_value=Decimal("0.851000")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["GBP"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.730000")
        )

        response = api_client.get(
            "/api/v1/exchange/rates/time-series/",
            {
                "source_currency": "USD",
                "date_from": "2024-05-21",
                "date_to": "2024-05-22"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["source_currency"] == "USD"
        assert len(response.data["rates"]) == 3  # 2 EUR + 1 GBP

    def test_time_series_missing_params(self, api_client):
        """
        Test time-series endpoint returns 400 when required params are missing.
        """
        response = api_client.get("/api/v1/exchange/rates/time-series/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_time_series_invalid_date_format(self, api_client):
        """
        Test time-series endpoint returns 400 for invalid date format.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/time-series/",
            {
                "source_currency": "USD",
                "date_from": "21-05-2024",  # Wrong format
                "date_to": "2024-05-22"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_time_series_date_from_after_date_to(self, api_client):
        """
        Test time-series endpoint returns 400 when date_from > date_to.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/time-series/",
            {
                "source_currency": "USD",
                "date_from": "2024-05-25",
                "date_to": "2024-05-20"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_time_series_currency_not_found(self, api_client):
        """
        Test time-series endpoint returns 404 when currency doesn't exist.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/time-series/",
            {
                "source_currency": "XXX",
                "date_from": "2024-05-21",
                "date_to": "2024-05-22"
            }
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    @patch('apps.exchange.api.v1.views.ExchangeRateService.convert_amount')
    def test_convert_success(self, mock_convert, api_client):
        """
        Test GET /api/v1/exchange/rates/convert/ successfully converts amount.
        """
        mock_convert.return_value = {
            "source_currency": "USD",
            "exchanged_currency": "EUR",
            "amount": Decimal("100"),
            "rate": Decimal("0.850000"),
            "converted_amount": Decimal("85.000000"),
            "valuation_date": date(2024, 5, 21)
        }

        response = api_client.get(
            "/api/v1/exchange/rates/convert/",
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": "100",
                "valuation_date": "2024-05-21"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["source_currency"] == "USD"
        assert response.data["exchanged_currency"] == "EUR"
        assert response.data["amount"] == "100"
        assert response.data["rate"] == "0.850000"
        assert response.data["converted_amount"] == "85.000000"

    def test_convert_missing_params(self, api_client):
        """
        Test convert endpoint returns 400 when required params are missing.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/convert/",
            {"source_currency": "USD"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_convert_invalid_amount(self, api_client):
        """
        Test convert endpoint returns 400 for invalid amount.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/convert/",
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": "not-a-number"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_convert_negative_amount(self, api_client):
        """
        Test convert endpoint returns 400 for negative amount.
        """
        response = api_client.get(
            "/api/v1/exchange/rates/convert/",
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": "-100"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    @patch('apps.exchange.api.v1.views.ExchangeRateService.convert_amount')
    def test_convert_service_fails(self, mock_convert, api_client):
        """
        Test convert endpoint returns 500 when service fails.
        """
        mock_convert.return_value = None

        response = api_client.get(
            "/api/v1/exchange/rates/convert/",
            {
                "source_currency": "USD",
                "exchanged_currency": "XXX",
                "amount": "100"
            }
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.data


@pytest.mark.django_db(transaction=True)
class TestProviderViewSet:
    """Tests for ProviderViewSet endpoints."""

    def setup_method(self):
        """Clean up before each test."""
        Provider.objects.all().delete()

    def test_list_providers(self, api_client):
        """
        Test GET /api/v1/exchange/providers/ lists all providers.
        """
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )
        Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=2,
            is_active=False
        )

        response = api_client.get("/api/v1/exchange/providers/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_retrieve_provider(self, api_client):
        """
        Test GET /api/v1/exchange/providers/{id}/ retrieves a single provider.
        """
        provider = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        response = api_client.get(f"/api/v1/exchange/providers/{provider.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == ProviderName.MOCK
        assert response.data["priority"] == 1

    def test_create_provider(self, api_client):
        """
        Test POST /api/v1/exchange/providers/ creates a new provider.
        """
        data = {
            "name": ProviderName.MOCK,
            "priority": 1,
            "is_active": True
        }
        response = api_client.post("/api/v1/exchange/providers/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Provider.objects.filter(name=ProviderName.MOCK).exists()

    def test_update_provider(self, api_client):
        """
        Test PUT /api/v1/exchange/providers/{id}/ updates a provider.
        """
        provider = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        data = {
            "name": ProviderName.MOCK,
            "priority": 5,
            "is_active": False
        }
        response = api_client.put(f"/api/v1/exchange/providers/{provider.id}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["priority"] == 5
        assert response.data["is_active"] is False

    def test_delete_provider(self, api_client):
        """
        Test DELETE /api/v1/exchange/providers/{id}/ deletes a provider.
        """
        provider = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        response = api_client.delete(f"/api/v1/exchange/providers/{provider.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Provider.objects.filter(id=provider.id).exists()
