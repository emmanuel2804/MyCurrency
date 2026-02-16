"""
Provider Registry - Maps ProviderName enum to adapter classes.
This is the glue between the database Provider model and the actual implementation.
"""

from apps.exchange.infrastructure.persistence.models import ProviderName
from apps.exchange.domain.interfaces import BaseExchangeRateProvider
from apps.exchange.infrastructure.providers.currency_beacon import CurrencyBeaconProvider
from apps.exchange.infrastructure.providers.mock import MockProvider
from apps.exchange.infrastructure.persistence.models import Provider


# Registry: Maps ProviderName enum to the corresponding adapter class
PROVIDER_REGISTRY: dict[str, type[BaseExchangeRateProvider]] = {
    ProviderName.CURRENCY_BEACON: CurrencyBeaconProvider,
    ProviderName.MOCK: MockProvider,
}


def get_provider_instance(provider_name: str) -> BaseExchangeRateProvider | None:
    """
    Get an instance of a provider by its name.

    Args:
        provider_name: The provider name from ProviderName enum

    Returns:
        Instance of the provider adapter, or None if not found
        
    """
    provider_class = PROVIDER_REGISTRY.get(provider_name)

    if provider_class is None:
        print(f"Provider '{provider_name}' not found in registry")
        return None

    return provider_class()


def get_active_providers_ordered() -> list[BaseExchangeRateProvider]:
    """
    Get all active providers from the database, ordered by priority.

    Returns:
        List of provider instances, sorted by priority (lowest number = highest priority)

    """

    # Query active providers ordered by priority
    active_providers = Provider.objects.filter(is_active=True).order_by('priority')

    # Instantiate each provider adapter
    provider_instances = []
    for provider_model in active_providers:
        instance = get_provider_instance(provider_model.name)
        if instance is not None:
            provider_instances.append(instance)

    return provider_instances
