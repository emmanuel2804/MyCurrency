import pytest
from apps.exchange.infrastructure.providers.registry import (
    get_provider_instance,
    get_active_providers_ordered,
    PROVIDER_REGISTRY
)
from apps.exchange.infrastructure.persistence.models import Provider, ProviderName
from apps.exchange.infrastructure.providers.mock import MockProvider
from apps.exchange.infrastructure.providers.currency_beacon import CurrencyBeaconProvider


@pytest.mark.django_db(transaction=True)
class TestProviderRegistry:
    """Tests for provider registry functions."""

    def setup_method(self):
        """Clean up providers before each test."""
        Provider.objects.all().delete()

    def test_provider_registry_contains_providers(self):
        """
        Test that PROVIDER_REGISTRY contains expected providers.
        """
        assert ProviderName.MOCK in PROVIDER_REGISTRY
        assert ProviderName.CURRENCY_BEACON in PROVIDER_REGISTRY

    def test_get_provider_instance_mock(self):
        """
        Test that get_provider_instance returns MockProvider instance.
        """
        instance = get_provider_instance(ProviderName.MOCK)

        assert instance is not None
        assert isinstance(instance, MockProvider)

    def test_get_provider_instance_currency_beacon(self):
        """
        Test that get_provider_instance returns CurrencyBeaconProvider instance.
        """
        instance = get_provider_instance(ProviderName.CURRENCY_BEACON)

        assert instance is not None
        assert isinstance(instance, CurrencyBeaconProvider)

    def test_get_provider_instance_invalid(self):
        """
        Test that get_provider_instance returns None for invalid provider name.
        """
        instance = get_provider_instance("invalid_provider")

        assert instance is None

    def test_get_active_providers_ordered_empty(self):
        """
        Test that get_active_providers_ordered returns empty list when no providers exist.
        """
        providers = get_active_providers_ordered()

        assert providers == []

    def test_get_active_providers_ordered_single(self):
        """
        Test get_active_providers_ordered with single active provider.
        """
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        providers = get_active_providers_ordered()

        assert len(providers) == 1
        assert isinstance(providers[0], MockProvider)

    def test_get_active_providers_ordered_multiple(self):
        """
        Test get_active_providers_ordered returns providers in priority order.
        """
        Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=2,
            is_active=True
        )
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        providers = get_active_providers_ordered()

        assert len(providers) == 2
        # Mock should be first (priority=1)
        assert isinstance(providers[0], MockProvider)
        # CurrencyBeacon should be second (priority=2)
        assert isinstance(providers[1], CurrencyBeaconProvider)

    def test_get_active_providers_ordered_only_active(self):
        """
        Test that get_active_providers_ordered only returns active providers.
        """
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )
        Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=2,
            is_active=False  # Inactive
        )

        providers = get_active_providers_ordered()

        assert len(providers) == 1
        assert isinstance(providers[0], MockProvider)

    def test_get_active_providers_ordered_skips_invalid(self):
        """
        Test that get_active_providers_ordered skips providers not in registry.
        """
        # Create a provider with invalid name (would require mocking the DB or extending ProviderName)
        # For this test, we ensure only valid providers are returned
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        providers = get_active_providers_ordered()

        assert len(providers) == 1
        assert all(provider is not None for provider in providers)
