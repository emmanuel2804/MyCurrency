"""
Django ORM models for persistence.
Infrastructure layer — technical storage detail.
"""

import uuid
from django.db import models


class BaseModel(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Currency(BaseModel):

    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=20, db_index=True)
    symbol = models.CharField(max_length=10)

    class Meta:
        verbose_name_plural = "currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.symbol})"


class CurrencyExchangeRate(BaseModel):

    source_currency = models.ForeignKey(
        Currency,
        related_name="source_exchanges",
        on_delete=models.CASCADE,
    )
    exchanged_currency = models.ForeignKey(
        Currency,
        related_name="exchanged_exchanges",
        on_delete=models.CASCADE,
    )
    valuation_date = models.DateField(db_index=True)
    rate_value = models.DecimalField(
        db_index=True,
        decimal_places=6,
        max_digits=18,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_currency", "exchanged_currency", "valuation_date"],
                name="unique_rate_per_day",
            )
        ]
        ordering = ["-valuation_date"]

    def __str__(self):
        return (
            f"From {self.source_currency.code} To {self.exchanged_currency.code} "
            f"| {self.valuation_date} | {self.rate_value}"
        )


class ProviderName(models.TextChoices):
    """
    Enum with available providers.
    To add a new provider:
    1. Add an entry here
    2. Implement the BaseExchangeRateProvider interface
    3. Register in PROVIDER_REGISTRY (providers/registry.py)
    """

    CURRENCY_BEACON = "currency_beacon", "CurrencyBeacon"
    MOCK = "mock", "Mock"
    EXCHANGE_RATE = "exchange_rate", "ExchangeRate"


class Provider(BaseModel):

    name = models.CharField(
        max_length=50,
        choices=ProviderName.choices,
        unique=True,
    )
    priority = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Lower number = higher priority. Determines the fallback order.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to exclude this provider from the fallback mechanism.",
    )

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.get_name_display()} (priority={self.priority}) (status={self.is_active})"