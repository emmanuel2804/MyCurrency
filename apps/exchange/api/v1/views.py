"""
ViewSets for the exchange API v1.
Each ViewSet exposes standard CRUD operations via DRF router.
"""

from decimal import Decimal
from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

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
from apps.exchange.domain.services import ExchangeRateService


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

    @extend_schema(
        parameters=[
            OpenApiParameter("source_currency", OpenApiTypes.STR, required=True, description="Source currency code (e.g. EUR)"),
            OpenApiParameter("date_from", OpenApiTypes.DATE, required=True, description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("date_to", OpenApiTypes.DATE, required=True, description="End date (YYYY-MM-DD)"),
        ],
        description="Get time series of exchange rates for a source currency"
    )
    @action(detail=False, methods=['get'], url_path='time-series')
    def time_series(self, request):
        """
        Get time series of exchange rates.

        Query params:
        - source_currency: Base currency code (required)
        - date_from: Start date YYYY-MM-DD (required)
        - date_to: End date YYYY-MM-DD (required)

        Returns:
        List of rates for all target currencies within the date range.
        If a rate doesn't exist in DB for a specific day, it will be fetched from providers.
        """
        source_currency_code = request.query_params.get('source_currency')
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')

        # Validation
        if not all([source_currency_code, date_from_str, date_to_str]):
            return Response(
                {"error": "source_currency, date_from, and date_to are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if date_from > date_to:
            return Response(
                {"error": "date_from must be before date_to"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create rates
        try:
            source_currency = Currency.objects.get(code=source_currency_code.upper())
        except Currency.DoesNotExist:
            return Response(
                {"error": f"Currency {source_currency_code} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Query existing rates
        rates = CurrencyExchangeRate.objects.filter(
            source_currency=source_currency,
            valuation_date__gte=date_from,
            valuation_date__lte=date_to
        ).select_related('source_currency', 'exchanged_currency')

        # Serialize and return
        serializer = self.get_serializer(rates, many=True)
        return Response({
            "source_currency": source_currency_code.upper(),
            "date_from": date_from_str,
            "date_to": date_to_str,
            "rates": serializer.data
        })

    @extend_schema(
        parameters=[
            OpenApiParameter("source_currency", OpenApiTypes.STR, required=True, description="Source currency code (e.g. EUR)"),
            OpenApiParameter("exchanged_currency", OpenApiTypes.STR, required=True, description="Target currency code (e.g. USD)"),
            OpenApiParameter("amount", OpenApiTypes.DECIMAL, required=True, description="Amount to convert"),
            OpenApiParameter("valuation_date", OpenApiTypes.DATE, description="Date for the rate (optional, defaults to today)"),
        ],
        description="Convert amount from one currency to another"
    )
    @action(detail=False, methods=['get'], url_path='convert')
    def convert(self, request):
        """
        Convert an amount from one currency to another.
        """
        
        source_currency_code = request.query_params.get('source_currency')
        exchanged_currency_code = request.query_params.get('exchanged_currency')
        amount_str = request.query_params.get('amount')
        valuation_date_str = request.query_params.get('valuation_date')

        # Validation
        if not all([source_currency_code, exchanged_currency_code, amount_str]):
            return Response(
                {"error": "source_currency, exchanged_currency, and amount are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(amount_str)
        except (ValueError, TypeError, Exception):
            return Response(
                {"error": "Invalid amount. Must be a number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be positive"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse valuation date
        valuation_date = None
        if valuation_date_str:
            try:
                valuation_date = datetime.strptime(valuation_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Use service to convert
        result = ExchangeRateService.convert_amount(
            source_currency_code.upper(),
            exchanged_currency_code.upper(),
            amount,
            valuation_date
        )

        if result is None:
            return Response(
                {"error": "Failed to get exchange rate. All providers failed or currencies not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Format response
        return Response({
            "source_currency": result["source_currency"],
            "exchanged_currency": result["exchanged_currency"],
            "amount": str(result["amount"]),
            "rate": str(result["rate"]),
            "converted_amount": str(result["converted_amount"]),
            "valuation_date": result["valuation_date"].strftime("%Y-%m-%d")
        })


@extend_schema(tags=['Providers'])
class ProviderViewSet(viewsets.ModelViewSet):

    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer