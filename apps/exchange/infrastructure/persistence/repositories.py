"""
Repository pattern implementation.
Abstracts database access to decouple domain logic from persistence.
"""

from typing import List, Optional
from datetime import date
from decimal import Decimal

from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
)


class CurrencyRepository:
    """Repository for Currency aggregate."""

    @staticmethod
    def get_by_code(code: str) -> Optional[Currency]:
        """Get currency by code."""
        try:
            return Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            return None

    @staticmethod
    def get_all_active() -> List[Currency]:
        """Get all currencies."""
        return list(Currency.objects.all())

    @staticmethod
    def create(code: str, name: str, symbol: str) -> Currency:
        """Create a new currency."""
        return Currency.objects.create(
            code=code.upper(),
            name=name,
            symbol=symbol
        )

    @staticmethod
    def exists(code: str) -> bool:
        """Check if currency exists."""
        return Currency.objects.filter(code=code.upper()).exists()

    @staticmethod
    def bulk_create(currencies: List[dict]) -> List[Currency]:
        """Bulk create currencies."""
        currency_objects = [
            Currency(
                code=c["code"].upper(),
                name=c["name"],
                symbol=c["symbol"]
            )
            for c in currencies
        ]
        return Currency.objects.bulk_create(
            currency_objects,
            ignore_conflicts=True
        )


class CurrencyExchangeRateRepository:
    """Repository for CurrencyExchangeRate aggregate."""

    @staticmethod
    def get_rate(
        source_currency: Currency,
        exchanged_currency: Currency,
        valuation_date: date
    ) -> Optional[CurrencyExchangeRate]:
        """Get exchange rate for specific date."""
        return CurrencyExchangeRate.objects.filter(
            source_currency=source_currency,
            exchanged_currency=exchanged_currency,
            valuation_date=valuation_date
        ).first()

    @staticmethod
    def get_rates_for_date_range(
        source_currency: Currency,
        date_from: date,
        date_to: date
    ) -> List[CurrencyExchangeRate]:
        """Get all rates for a currency within date range."""
        return list(
            CurrencyExchangeRate.objects
            .filter(
                source_currency=source_currency,
                valuation_date__gte=date_from,
                valuation_date__lte=date_to
            )
            .select_related('source_currency', 'exchanged_currency')
            .order_by('valuation_date', 'exchanged_currency__code')
        )

    @staticmethod
    def create(
        source_currency: Currency,
        exchanged_currency: Currency,
        valuation_date: date,
        rate_value: Decimal
    ) -> CurrencyExchangeRate:
        """Create a new exchange rate."""
        return CurrencyExchangeRate.objects.create(
            source_currency=source_currency,
            exchanged_currency=exchanged_currency,
            valuation_date=valuation_date,
            rate_value=rate_value
        )

    @staticmethod
    def bulk_create(rates: List[dict]) -> List[CurrencyExchangeRate]:
        """Bulk create exchange rates."""
        rate_objects = [
            CurrencyExchangeRate(
                source_currency=r["source_currency"],
                exchanged_currency=r["exchanged_currency"],
                valuation_date=r["valuation_date"],
                rate_value=r["rate_value"]
            )
            for r in rates
        ]
        return CurrencyExchangeRate.objects.bulk_create(
            rate_objects,
            ignore_conflicts=True
        )

    @staticmethod
    def delete_older_than(days: int) -> int:
        """Delete rates older than specified days."""
        from django.utils import timezone
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
        deleted, _ = CurrencyExchangeRate.objects.filter(
            valuation_date__lt=cutoff_date
        ).delete()
        return deleted

    @staticmethod
    def get_latest_rate_date(source_currency: Currency) -> Optional[date]:
        """Get the most recent date with rates for a currency."""
        latest = CurrencyExchangeRate.objects.filter(
            source_currency=source_currency
        ).order_by('-valuation_date').first()
        return latest.valuation_date if latest else None


class ProviderRepository:
    """Repository for Provider aggregate."""

    @staticmethod
    def get_active_ordered() -> List[Provider]:
        """Get all active providers ordered by priority."""
        return list(
            Provider.objects
            .filter(is_active=True)
            .order_by('priority')
        )

    @staticmethod
    def get_by_name(name: str) -> Optional[Provider]:
        """Get provider by name."""
        try:
            return Provider.objects.get(name=name)
        except Provider.DoesNotExist:
            return None

    @staticmethod
    def update_priority(provider: Provider, new_priority: int) -> Provider:
        """Update provider priority."""
        provider.priority = new_priority
        provider.save()
        return provider

    @staticmethod
    def toggle_active(provider: Provider) -> Provider:
        """Toggle provider active status."""
        provider.is_active = not provider.is_active
        provider.save()
        return provider

    @staticmethod
    def get_all() -> List[Provider]:
        """Get all providers."""
        return list(Provider.objects.all())
