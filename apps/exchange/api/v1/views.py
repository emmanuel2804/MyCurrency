"""
ViewSets for the exchange API v1.
Each ViewSet exposes standard CRUD operations via DRF router.
"""

from rest_framework import viewsets
from drf_spectacular.utils import extend_schema

from apps.exchange.api.v1.serializers import (
    CurrencyExchangeRateSerializer,
    CurrencySerializer,
    ProviderSerializer,
)
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
)


@extend_schema(tags=['Currencies'])
class CurrencyViewSet(viewsets.ModelViewSet):

    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


@extend_schema(tags=['Rates'])
class CurrencyExchangeRateViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = CurrencyExchangeRate.objects.select_related(
        "source_currency",
        "exchanged_currency",
    ).all()
    serializer_class = CurrencyExchangeRateSerializer


@extend_schema(tags=['Providers'])
class ProviderViewSet(viewsets.ModelViewSet):

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer