import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.exchange.infrastructure.persistence.repositories import (
    CurrencyRepository,
    CurrencyExchangeRateRepository,
    ProviderRepository
)
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
    ProviderName
)


@pytest.mark.django_db(transaction=True)
class TestCurrencyRepository:
    """Tests for CurrencyRepository."""

    def setup_method(self):
        """Clean up before each test."""
        Currency.objects.all().delete()

    def test_get_by_code_success(self):
        """Test get_by_code returns currency when it exists."""
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")

        currency = CurrencyRepository.get_by_code("USD")

        assert currency is not None
        assert currency.code == "USD"

    def test_get_by_code_case_insensitive(self):
        """Test get_by_code is case insensitive."""
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")

        currency = CurrencyRepository.get_by_code("usd")

        assert currency is not None
        assert currency.code == "USD"

    def test_get_by_code_not_found(self):
        """Test get_by_code returns None when currency doesn't exist."""
        currency = CurrencyRepository.get_by_code("XXX")

        assert currency is None

    def test_get_all_active(self):
        """Test get_all_active returns all currencies."""
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        Currency.objects.create(code="EUR", name="Euro", symbol="€")

        currencies = CurrencyRepository.get_all_active()

        assert len(currencies) == 2

    def test_create(self):
        """Test create creates a new currency."""
        currency = CurrencyRepository.create("USD", "US Dollar", "$")

        assert currency.code == "USD"
        assert Currency.objects.filter(code="USD").exists()

    def test_create_uppercase_code(self):
        """Test create converts code to uppercase."""
        currency = CurrencyRepository.create("usd", "US Dollar", "$")

        assert currency.code == "USD"

    def test_exists_true(self):
        """Test exists returns True when currency exists."""
        Currency.objects.create(code="USD", name="US Dollar", symbol="$")

        assert CurrencyRepository.exists("USD") is True

    def test_exists_false(self):
        """Test exists returns False when currency doesn't exist."""
        assert CurrencyRepository.exists("XXX") is False

    def test_bulk_create(self):
        """Test bulk_create creates multiple currencies."""
        currencies_data = [
            {"code": "USD", "name": "US Dollar", "symbol": "$"},
            {"code": "EUR", "name": "Euro", "symbol": "€"},
        ]

        created = CurrencyRepository.bulk_create(currencies_data)

        assert len(created) == 2
        assert Currency.objects.count() == 2


@pytest.mark.django_db(transaction=True)
class TestCurrencyExchangeRateRepository:
    """Tests for CurrencyExchangeRateRepository."""

    def setup_method(self):
        """Clean up before each test."""
        CurrencyExchangeRate.objects.all().delete()
        Currency.objects.all().delete()

    @pytest.fixture
    def currencies(self):
        """Create test currencies."""
        usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
        eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
        return {"USD": usd, "EUR": eur}

    def test_get_rate_success(self, currencies):
        """Test get_rate returns rate when it exists."""
        test_date = date(2024, 5, 21)
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=test_date,
            rate_value=Decimal("0.85")
        )

        rate = CurrencyExchangeRateRepository.get_rate(
            currencies["USD"],
            currencies["EUR"],
            test_date
        )

        assert rate is not None
        assert rate.rate_value == Decimal("0.85")

    def test_get_rate_not_found(self, currencies):
        """Test get_rate returns None when rate doesn't exist."""
        test_date = date(2024, 5, 21)

        rate = CurrencyExchangeRateRepository.get_rate(
            currencies["USD"],
            currencies["EUR"],
            test_date
        )

        assert rate is None

    def test_get_rates_for_date_range(self, currencies):
        """Test get_rates_for_date_range returns rates within range."""
        date1 = date(2024, 5, 21)
        date2 = date(2024, 5, 22)
        date3 = date(2024, 5, 23)

        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date1,
            rate_value=Decimal("0.85")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date2,
            rate_value=Decimal("0.86")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date3,
            rate_value=Decimal("0.87")
        )

        rates = CurrencyExchangeRateRepository.get_rates_for_date_range(
            currencies["USD"],
            date1,
            date2
        )

        assert len(rates) == 2
        assert rates[0].valuation_date == date1
        assert rates[1].valuation_date == date2

    def test_create(self, currencies):
        """Test create creates a new rate."""
        test_date = date(2024, 5, 21)

        rate = CurrencyExchangeRateRepository.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=test_date,
            rate_value=Decimal("0.85")
        )

        assert rate.rate_value == Decimal("0.85")
        assert CurrencyExchangeRate.objects.filter(
            source_currency=currencies["USD"],
            valuation_date=test_date
        ).exists()

    def test_bulk_create(self, currencies):
        """Test bulk_create creates multiple rates."""
        rates_data = [
            {
                "source_currency": currencies["USD"],
                "exchanged_currency": currencies["EUR"],
                "valuation_date": date(2024, 5, 21),
                "rate_value": Decimal("0.85")
            },
            {
                "source_currency": currencies["USD"],
                "exchanged_currency": currencies["EUR"],
                "valuation_date": date(2024, 5, 22),
                "rate_value": Decimal("0.86")
            },
        ]

        created = CurrencyExchangeRateRepository.bulk_create(rates_data)

        assert len(created) == 2

    def test_delete_older_than(self, currencies):
        """Test delete_older_than removes old rates."""
        old_date = date.today() - timedelta(days=100)
        recent_date = date.today() - timedelta(days=10)

        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=old_date,
            rate_value=Decimal("0.85")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=recent_date,
            rate_value=Decimal("0.86")
        )

        deleted_count = CurrencyExchangeRateRepository.delete_older_than(days=90)

        assert deleted_count == 1
        assert CurrencyExchangeRate.objects.count() == 1

    def test_get_latest_rate_date(self, currencies):
        """Test get_latest_rate_date returns most recent date."""
        date1 = date(2024, 5, 21)
        date2 = date(2024, 5, 25)

        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date1,
            rate_value=Decimal("0.85")
        )
        CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date2,
            rate_value=Decimal("0.86")
        )

        latest_date = CurrencyExchangeRateRepository.get_latest_rate_date(currencies["USD"])

        assert latest_date == date2


@pytest.mark.django_db(transaction=True)
class TestProviderRepository:
    """Tests for ProviderRepository."""

    def setup_method(self):
        """Clean up before each test."""
        Provider.objects.all().delete()

    def test_get_active_ordered(self):
        """Test get_active_ordered returns active providers in priority order."""
        Provider.objects.create(name=ProviderName.CURRENCY_BEACON, priority=2, is_active=True)
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        providers = ProviderRepository.get_active_ordered()

        assert len(providers) == 2
        assert providers[0].priority == 1
        assert providers[1].priority == 2

    def test_get_active_ordered_excludes_inactive(self):
        """Test get_active_ordered excludes inactive providers."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)
        Provider.objects.create(name=ProviderName.CURRENCY_BEACON, priority=2, is_active=False)

        providers = ProviderRepository.get_active_ordered()

        assert len(providers) == 1
        assert providers[0].name == ProviderName.MOCK

    def test_get_by_name_success(self):
        """Test get_by_name returns provider when it exists."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        provider = ProviderRepository.get_by_name(ProviderName.MOCK)

        assert provider is not None
        assert provider.name == ProviderName.MOCK

    def test_get_by_name_not_found(self):
        """Test get_by_name returns None when provider doesn't exist."""
        provider = ProviderRepository.get_by_name(ProviderName.MOCK)

        assert provider is None

    def test_update_priority(self):
        """Test update_priority updates provider priority."""
        provider = Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        updated = ProviderRepository.update_priority(provider, 5)

        assert updated.priority == 5
        provider.refresh_from_db()
        assert provider.priority == 5

    def test_toggle_active(self):
        """Test toggle_active toggles provider active status."""
        provider = Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)

        updated = ProviderRepository.toggle_active(provider)

        assert updated.is_active is False
        provider.refresh_from_db()
        assert provider.is_active is False

    def test_get_all(self):
        """Test get_all returns all providers."""
        Provider.objects.create(name=ProviderName.MOCK, priority=1, is_active=True)
        Provider.objects.create(name=ProviderName.CURRENCY_BEACON, priority=2, is_active=False)

        providers = ProviderRepository.get_all()

        assert len(providers) == 2
