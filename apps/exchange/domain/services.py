"""
Domain services - Core business logic.
Implements the fallback chain pattern for exchange rate providers.
"""

from decimal import Decimal
from datetime import date

from apps.exchange.infrastructure.persistence.models import Currency, CurrencyExchangeRate
from apps.exchange.infrastructure.providers.registry import get_active_providers_ordered


class ExchangeRateService:
    """
    Domain service that handles exchange rate retrieval with fallback mechanism.
    """

    @staticmethod
    def get_exchange_rate(
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: date
    ) -> Decimal | None:
        """
        Get exchange rate with fallback mechanism.

        Checks database first, then queries providers in priority order.
        Saves successful result to database for future use.

        Returns exchange rate as Decimal, or None if all providers fail.
        """
        try:
            source_currency = Currency.objects.get(code=source_currency_code)
            exchanged_currency = Currency.objects.get(code=exchanged_currency_code)

            existing_rate = CurrencyExchangeRate.objects.filter(
                source_currency=source_currency,
                exchanged_currency=exchanged_currency,
                valuation_date=valuation_date
            ).first()

            if existing_rate:
                return existing_rate.rate_value

        except Currency.DoesNotExist:
            return None

        providers = get_active_providers_ordered()

        if not providers:
            return None

        rate_value = None

        for provider in providers:
            rate_value = provider.get_exchange_rate_data(
                source_currency_code,
                exchanged_currency_code,
                valuation_date
            )

            if rate_value is not None:
                break

        if rate_value is not None:
            try:
                CurrencyExchangeRate.objects.create(
                    source_currency=source_currency,
                    exchanged_currency=exchanged_currency,
                    valuation_date=valuation_date,
                    rate_value=rate_value
                )
            except Exception:
                pass

        return rate_value

    @staticmethod
    def convert_amount(
        source_currency_code: str,
        exchanged_currency_code: str,
        amount: Decimal,
        valuation_date: date | None = None
    ) -> dict | None:
        """
        Convert an amount from one currency to another.

        Returns dict with conversion details, or None if conversion fails.
        """
        if valuation_date is None:
            valuation_date = date.today()

        rate = ExchangeRateService.get_exchange_rate(
            source_currency_code,
            exchanged_currency_code,
            valuation_date
        )

        if rate is None:
            return None

        converted_amount = (amount * rate).quantize(Decimal("0.000001"))

        return {
            "source_currency": source_currency_code,
            "exchanged_currency": exchanged_currency_code,
            "amount": amount,
            "rate": rate,
            "converted_amount": converted_amount,
            "valuation_date": valuation_date
        }
