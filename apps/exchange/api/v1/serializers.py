"""
Serializers for the exchange bounded context.
Handles validation and transformation between API and ORM layers.
"""

from rest_framework import serializers

from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
    ProviderName,
)


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value: str) -> str:
        return value.upper()


class CurrencyExchangeRateSerializer(serializers.ModelSerializer):
    source_currency = CurrencySerializer(read_only=True)
    exchanged_currency = CurrencySerializer(read_only=True)

    class Meta:
        model = CurrencyExchangeRate
        fields = [
            "id",
            "source_currency",
            "exchanged_currency",
            "valuation_date",
            "rate_value",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProviderSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(
        source="get_name_display",
        read_only=True,
    )

    class Meta:
        model = Provider
        fields = ["id", "name", "name_display", "priority", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]