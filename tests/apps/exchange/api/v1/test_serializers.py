import pytest
from decimal import Decimal
from datetime import date
from apps.exchange.api.v1.serializers import (
    CurrencySerializer,
    CurrencyExchangeRateSerializer,
    ProviderSerializer
)
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
    ProviderName
)


@pytest.fixture
def currencies(db):
    """Create test currencies."""
    Currency.objects.all().delete()
    usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    return {"USD": usd, "EUR": eur}


@pytest.mark.django_db(transaction=True)
class TestCurrencySerializer:
    """Tests for CurrencySerializer."""

    def setup_method(self):
        """Clean up before each test."""
        Currency.objects.all().delete()

    def test_serialize_currency(self, currencies):
        """
        Test that CurrencySerializer correctly serializes a Currency instance.
        """
        serializer = CurrencySerializer(currencies["USD"])
        data = serializer.data

        assert data["code"] == "USD"
        assert data["name"] == "US Dollar"
        assert data["symbol"] == "$"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_deserialize_currency(self):
        """
        Test that CurrencySerializer correctly deserializes data.
        """
        data = {
            "code": "gbp",
            "name": "British Pound",
            "symbol": "£"
        }
        serializer = CurrencySerializer(data=data)

        assert serializer.is_valid()
        currency = serializer.save()

        assert currency.code == "GBP"  # Should be uppercased
        assert currency.name == "British Pound"
        assert currency.symbol == "£"

    def test_validate_code_uppercase(self):
        """
        Test that currency code is converted to uppercase.
        """
        data = {
            "code": "chf",
            "name": "Swiss Franc",
            "symbol": "CHF"
        }
        serializer = CurrencySerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data["code"] == "CHF"

    def test_read_only_fields(self, currencies):
        """
        Test that id, created_at, and updated_at are read-only.
        """
        original_id = str(currencies["USD"].id)
        data = {
            "id": "new-id",
            "code": "USD",
            "name": "Updated Name",
            "symbol": "$$",  # Required field
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z"
        }

        serializer = CurrencySerializer(currencies["USD"], data=data, partial=False)
        assert serializer.is_valid(), serializer.errors
        currency = serializer.save()

        # Read-only fields should not be updated
        assert str(currency.id) == original_id
        assert currency.name == "Updated Name"
        assert currency.symbol == "$$"


@pytest.mark.django_db(transaction=True)
class TestCurrencyExchangeRateSerializer:
    """Tests for CurrencyExchangeRateSerializer."""

    def setup_method(self):
        """Clean up before each test."""
        CurrencyExchangeRate.objects.all().delete()
        Currency.objects.all().delete()

    def test_serialize_exchange_rate(self, currencies):
        """
        Test that CurrencyExchangeRateSerializer correctly serializes a rate.
        """
        rate = CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.850000")
        )

        serializer = CurrencyExchangeRateSerializer(rate)
        data = serializer.data

        assert data["source_currency"]["code"] == "USD"
        assert data["exchanged_currency"]["code"] == "EUR"
        assert data["valuation_date"] == "2024-05-21"
        assert Decimal(data["rate_value"]) == Decimal("0.850000")
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_nested_currency_serialization(self, currencies):
        """
        Test that nested currencies are fully serialized.
        """
        rate = CurrencyExchangeRate.objects.create(
            source_currency=currencies["USD"],
            exchanged_currency=currencies["EUR"],
            valuation_date=date(2024, 5, 21),
            rate_value=Decimal("0.850000")
        )

        serializer = CurrencyExchangeRateSerializer(rate)
        data = serializer.data

        # Nested currencies should have full details
        assert "name" in data["source_currency"]
        assert "symbol" in data["source_currency"]
        assert data["source_currency"]["name"] == "US Dollar"
        assert data["exchanged_currency"]["symbol"] == "€"


@pytest.mark.django_db(transaction=True)
class TestProviderSerializer:
    """Tests for ProviderSerializer."""

    def setup_method(self):
        """Clean up before each test."""
        Provider.objects.all().delete()

    def test_serialize_provider(self):
        """
        Test that ProviderSerializer correctly serializes a Provider.
        """
        provider = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        serializer = ProviderSerializer(provider)
        data = serializer.data

        assert data["name"] == ProviderName.MOCK
        assert data["name_display"] == "Mock"
        assert data["priority"] == 1
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_deserialize_provider(self):
        """
        Test that ProviderSerializer correctly deserializes data.
        """
        data = {
            "name": ProviderName.CURRENCY_BEACON,
            "priority": 2,
            "is_active": False
        }
        serializer = ProviderSerializer(data=data)

        assert serializer.is_valid()
        provider = serializer.save()

        assert provider.name == ProviderName.CURRENCY_BEACON
        assert provider.priority == 2
        assert provider.is_active is False

    def test_name_display_read_only(self):
        """
        Test that name_display is read-only and generated from name.
        """
        provider = Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=1,
            is_active=True
        )

        serializer = ProviderSerializer(provider)
        data = serializer.data

        assert data["name_display"] == "CurrencyBeacon"
        assert "name_display" not in serializer.Meta.fields or \
               "name_display" in serializer.fields and serializer.fields["name_display"].read_only

    def test_update_provider(self):
        """
        Test updating a provider through serializer.
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
        serializer = ProviderSerializer(provider, data=data)

        assert serializer.is_valid()
        updated_provider = serializer.save()

        assert updated_provider.priority == 5
        assert updated_provider.is_active is False
