from decimal import Decimal
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.exchange.infrastructure.persistence.models import ProviderName
from apps.exchange.infrastructure.providers.registry import PROVIDER_REGISTRY
from core.settings import EXCHANGERATE_API_KEY, EXCHANGERATE_URL


def get_exchange_rate_provider():
    """
    Returns the ExchangeRateProvider instance or None if not available.

    Checks both that the enum entry exists in the registry and that the
    required environment variables are configured.
    """
    if ProviderName.EXCHANGE_RATE not in PROVIDER_REGISTRY:
        return None, "Provider 'exchange_rate' is not registered in PROVIDER_REGISTRY"

    if not EXCHANGERATE_URL or not EXCHANGERATE_API_KEY:
        return None, "Provider not configured: EXCHANGERATE_URL and EXCHANGERATE_KEY must be set"

    return PROVIDER_REGISTRY[ProviderName.EXCHANGE_RATE](), None


@extend_schema(tags=['Rates v2'])
class ExchangeRateV2ViewSet(viewsets.ViewSet):

    @extend_schema(
        parameters=[
            OpenApiParameter("source_currency", OpenApiTypes.STR, required=True, description="Source currency code (e.g. EUR)"),
            OpenApiParameter("exchanged_currency", OpenApiTypes.STR, required=True, description="Target currency code (e.g. USD)"),
            OpenApiParameter("amount", OpenApiTypes.DECIMAL, required=True, description="Amount to convert"),
        ],
        description="Convert amount between currencies using ExchangeRate provider exclusively. Only returns the rate for today's date."
    )
    @action(detail=False, methods=['get'], url_path='convert')
    def convert(self, request):
        provider, error = get_exchange_rate_provider()
        if error or provider is None:
            return Response({"error": error}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        source_currency_code = request.query_params.get('source_currency')
        exchanged_currency_code = request.query_params.get('exchanged_currency')
        amount_str = request.query_params.get('amount')

        if not all([source_currency_code, exchanged_currency_code, amount_str]):
            return Response(
                {"error": "source_currency, exchanged_currency, and amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(amount_str)
        except Exception:
            return Response(
                {"error": "Invalid amount. Must be a number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )

        rate_value = provider.get_exchange_rate_data(
            source_currency_code.upper(),
            exchanged_currency_code.upper(),
            datetime.today().date()
        )

        if rate_value is None:
            return Response(
                {"error": f"Could not get exchange rate from ExchangeRate provider"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        converted_amount = (amount * rate_value).quantize(Decimal("0.000001"))

        return Response({
            "provider": "exchange_rate",
            "source_currency": source_currency_code.upper(),
            "exchanged_currency": exchanged_currency_code.upper(),
            "amount": str(amount),
            "rate": str(rate_value),
            "converted_amount": str(converted_amount),
            "valuation_date": datetime.today().strftime("%Y-%m-%d")
        })
