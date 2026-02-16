import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock

from apps.exchange.domain.services import ExchangeRateService
from apps.exchange.infrastructure.persistence.models import Currency, CurrencyExchangeRate, Provider, ProviderName
from apps.exchange.infrastructure.providers.mock import MockProvider


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
class TestExchangeRateService:
    """Tests for ExchangeRateService domain service."""

    def setup_method(self):
        """Clean up before each test."""
        CurrencyExchangeRate.objects.all().delete()
        Currency.objects.all().delete()
        Provider.objects.all().delete()

    def test_get_exchange_rate_from_database(self, currencies):
        """
        Test that get_exchange_rate returns rate from database when it exists.
        """
        # Create existing rate in DB
        test_date = date(2024, 5, 21)
        rate_value = Decimal("0.850000")

        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=test_date,
            rate_value=rate_value
        )

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        assert result == rate_value

    def test_get_exchange_rate_currency_not_found(self, db):
        """
        Test that get_exchange_rate returns None when currency doesn't exist.
        """
        test_date = date(2024, 5, 21)

        result = ExchangeRateService.get_exchange_rate("XXX", "YYY", test_date)

        assert result is None

    @patch('apps.exchange.domain.services.get_active_providers_ordered')
    def test_get_exchange_rate_no_providers(self, mock_get_providers, currencies):
        """
        Test that get_exchange_rate returns None when no providers are active.
        """
        mock_get_providers.return_value = []
        test_date = date(2024, 5, 21)

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        assert result is None

    @patch('apps.exchange.domain.services.get_active_providers_ordered')
    def test_get_exchange_rate_from_provider(self, mock_get_providers, currencies, mock_provider_active):
        """
        Test that get_exchange_rate fetches from provider when not in DB.
        """
        # Setup mock provider
        mock_provider = MockProvider()
        mock_get_providers.return_value = [mock_provider]

        test_date = date(2024, 5, 21)

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        assert result is not None
        assert isinstance(result, Decimal)
        assert result > 0

    @patch('apps.exchange.domain.services.get_active_providers_ordered')
    def test_get_exchange_rate_saves_to_database(self, mock_get_providers, currencies, mock_provider_active):
        """
        Test that get_exchange_rate saves fetched rate to database.
        """
        # Setup mock provider
        mock_provider = MockProvider()
        mock_get_providers.return_value = [mock_provider]

        test_date = date(2024, 5, 21)

        # Verify rate doesn't exist before
        assert not CurrencyExchangeRate.objects.filter(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=test_date
        ).exists()

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        # Verify rate was saved to DB
        assert result is not None
        saved_rate = CurrencyExchangeRate.objects.get(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=test_date
        )
        assert saved_rate.rate_value == result

    @patch('apps.exchange.domain.services.get_active_providers_ordered')
    def test_get_exchange_rate_fallback_mechanism(self, mock_get_providers, currencies, mock_provider_active):
        """
        Test that get_exchange_rate tries providers in order until one succeeds.
        """
        # Create mock providers - first fails, second succeeds
        failing_provider = MagicMock()
        failing_provider.get_exchange_rate_data.return_value = None

        successful_provider = MockProvider()

        mock_get_providers.return_value = [failing_provider, successful_provider]

        test_date = date(2024, 5, 21)

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        assert result is not None
        assert isinstance(result, Decimal)
        # Verify first provider was called
        failing_provider.get_exchange_rate_data.assert_called_once()

    @patch('apps.exchange.domain.services.get_active_providers_ordered')
    def test_get_exchange_rate_all_providers_fail(self, mock_get_providers, currencies, mock_provider_active):
        """
        Test that get_exchange_rate returns None when all providers fail.
        """
        # Create mock provider that fails
        failing_provider = MagicMock()
        failing_provider.get_exchange_rate_data.return_value = None

        mock_get_providers.return_value = [failing_provider]

        test_date = date(2024, 5, 21)

        result = ExchangeRateService.get_exchange_rate("USD", "EUR", test_date)

        assert result is None

    @patch('apps.exchange.domain.services.ExchangeRateService.get_exchange_rate')
    def test_convert_amount_success(self, mock_get_rate, currencies):
        """
        Test convert_amount with successful rate retrieval.
        """
        mock_get_rate.return_value = Decimal("0.850000")
        amount = Decimal("100")
        test_date = date(2024, 5, 21)

        result = ExchangeRateService.convert_amount("USD", "EUR", amount, test_date)

        assert result is not None
        assert result["source_currency"] == "USD"
        assert result["exchanged_currency"] == "EUR"
        assert result["amount"] == amount
        assert result["rate"] == Decimal("0.850000")
        assert result["converted_amount"] == Decimal("85.000000")
        assert result["valuation_date"] == test_date

    @patch('apps.exchange.domain.services.ExchangeRateService.get_exchange_rate')
    def test_convert_amount_no_rate(self, mock_get_rate):
        """
        Test convert_amount returns None when rate cannot be retrieved.
        """
        mock_get_rate.return_value = None
        amount = Decimal("100")

        result = ExchangeRateService.convert_amount("USD", "XXX", amount)

        assert result is None

    @patch('apps.exchange.domain.services.ExchangeRateService.get_exchange_rate')
    def test_convert_amount_default_date(self, mock_get_rate):
        """
        Test convert_amount uses today's date when valuation_date is None.
        """
        mock_get_rate.return_value = Decimal("0.850000")
        amount = Decimal("100")

        result = ExchangeRateService.convert_amount("USD", "EUR", amount)

        assert result is not None
        assert result["valuation_date"] == date.today()

    @patch('apps.exchange.domain.services.ExchangeRateService.get_exchange_rate')
    def test_convert_amount_precision(self, mock_get_rate):
        """
        Test convert_amount maintains 6 decimal places precision.
        """
        mock_get_rate.return_value = Decimal("1.234567")
        amount = Decimal("100")

        result = ExchangeRateService.convert_amount("USD", "EUR", amount)

        assert result is not None
        # Result should be quantized to 6 decimal places
        assert str(result["converted_amount"]).count(".") == 1
        decimal_places = len(str(result["converted_amount"]).split(".")[1])
        assert decimal_places <= 6
