import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from apps.exchange.application.tasks import (
    sync_exchange_rates_for_today,
    cleanup_old_exchange_rates,
    check_providers_health,
    sync_missing_rates_for_currency_pair
)
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
    ProviderName
)


@pytest.mark.django_db(transaction=True)
class TestCeleryTasks:
    """Tests for Celery background tasks."""

    def setup_method(self):
        """Clean up before each test."""
        CurrencyExchangeRate.objects.all().delete()
        Currency.objects.all().delete()
        Provider.objects.all().delete()

    def test_sync_exchange_rates_no_currencies(self):
        """Test sync task when no currencies exist."""
        result = sync_exchange_rates_for_today()

        assert result["success"] is False
        assert "No currencies" in result["message"]
        assert result["rates_synced"] == 0

    def test_sync_exchange_rates_no_providers(self):
        """Test sync task when no providers are active."""
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        Currency.objects.create(code="EUR", name="Euro", symbol="€")

        result = sync_exchange_rates_for_today()

        assert result["success"] is False
        assert "No active providers" in result["message"]

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_sync_exchange_rates_success(self, mock_get_provider):
        """Test successful rate synchronization."""
        # Setup currencies and provider
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Mock provider instance
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.return_value = Decimal("0.85")
        mock_get_provider.return_value = mock_provider

        result = sync_exchange_rates_for_today()

        assert result["success"] is True
        assert result["rates_synced"] > 0

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_sync_exchange_rates_skips_existing(self, mock_get_provider):
        """Test that sync skips rates that already exist."""
        # Setup
        usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Create existing rate for USD->EUR
        today = date.today()
        CurrencyExchangeRate.objects.create(
            source_currency=usd,
            exchanged_currency=eur,
            valuation_date=today,
            rate_value=Decimal("0.85")
        )

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.return_value = Decimal("0.86")
        mock_get_provider.return_value = mock_provider

        result = sync_exchange_rates_for_today()

        # Should not duplicate USD->EUR, but should create EUR->USD
        # Total should be 2: existing USD->EUR + new EUR->USD
        assert CurrencyExchangeRate.objects.count() == 2

        # Verify the existing rate wasn't modified
        existing_rate = CurrencyExchangeRate.objects.get(
            source_currency=usd,
            exchanged_currency=eur
        )
        assert existing_rate.rate_value == Decimal("0.85")

    def test_cleanup_old_exchange_rates(self):
        """Test cleanup of old exchange rates."""
        # Setup
        usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")

        # Create old and recent rates
        old_date = date.today() - timedelta(days=100)
        recent_date = date.today() - timedelta(days=10)

        CurrencyExchangeRate.objects.create(
            source_currency=usd,
            exchanged_currency=eur,
            valuation_date=old_date,
            rate_value=Decimal("0.85")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=usd,
            exchanged_currency=eur,
            valuation_date=recent_date,
            rate_value=Decimal("0.86")
        )

        result = cleanup_old_exchange_rates(days_to_keep=90)

        assert result["success"] is True
        assert result["rates_deleted"] == 1
        assert CurrencyExchangeRate.objects.count() == 1

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_check_providers_health_all_healthy(self, mock_get_provider):
        """Test provider health check when all providers are healthy."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Mock healthy provider
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.return_value = Decimal("0.85")
        mock_get_provider.return_value = mock_provider

        result = check_providers_health()

        assert result["success"] is True
        assert result["providers_checked"] == 1
        assert result["results"][ProviderName.MOCK]["status"] == "healthy"

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_check_providers_health_unhealthy(self, mock_get_provider):
        """Test provider health check with unhealthy provider."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Mock unhealthy provider
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.return_value = None
        mock_get_provider.return_value = mock_provider

        result = check_providers_health()

        assert result["success"] is True
        assert result["results"][ProviderName.MOCK]["status"] == "unhealthy"

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_check_providers_health_error(self, mock_get_provider):
        """Test provider health check when provider raises error."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Mock provider that raises error
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.side_effect = Exception("API Error")
        mock_get_provider.return_value = mock_provider

        result = check_providers_health()

        assert result["success"] is True
        assert result["results"][ProviderName.MOCK]["status"] == "error"
        assert "API Error" in result["results"][ProviderName.MOCK]["message"]

    @patch('apps.exchange.application.tasks.get_provider_instance')
    def test_sync_missing_rates_for_currency_pair(self, mock_get_provider):
        """Test syncing missing rates for specific currency pair."""
        # Setup
        usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.get_exchange_rate_data.return_value = Decimal("0.85")
        mock_get_provider.return_value = mock_provider

        date_from = date(2024, 5, 21)
        date_to = date(2024, 5, 23)

        result = sync_missing_rates_for_currency_pair(
            "USD",
            "EUR",
            date_from.isoformat(),
            date_to.isoformat()
        )

        assert result["success"] is True
        assert result["rates_synced"] == 3  # 3 days
        assert result["currency_pair"] == "USD/EUR"

    def test_sync_missing_rates_invalid_date(self):
        """Test sync with invalid date format."""
        result = sync_missing_rates_for_currency_pair(
            "USD",
            "EUR",
            "invalid-date",
            "2024-05-23"
        )

        assert result["success"] is False
        assert "Invalid date format" in result["message"]

    def test_sync_missing_rates_currency_not_found(self):
        """Test sync when currency doesn't exist."""
        result = sync_missing_rates_for_currency_pair(
            "XXX",
            "YYY",
            "2024-05-21",
            "2024-05-23"
        )

        assert result["success"] is False
        assert "Currency not found" in result["message"]
