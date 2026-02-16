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

    Fallback strategy:
    1. Check if rate exists in database
    2. If not, query providers in priority order
    3. If provider fails, try next one
    4. Save successful result to database
    5. Return None if all providers fail
    """

    @staticmethod
    def get_exchange_rate(
        source_currency_code: str,
        exchanged_currency_code: str,
        valuation_date: date
    ) -> Decimal | None:
        """
        Get exchange rate with fallback mechanism.

        Args:
            source_currency_code: Base currency (e.g. "USD")
            exchanged_currency_code: Target currency (e.g. "EUR")
            valuation_date: Date for the rate

        Returns:
            Exchange rate as Decimal, or None if all providers fail

        Example:
            >>> rate = ExchangeRateService.get_exchange_rate("USD", "EUR", date(2024, 1, 15))
            >>> if rate:
            ...     converted = 100 * rate
        """
        # Step 1: Check database first
        try:
            source_currency = Currency.objects.get(code=source_currency_code)
            exchanged_currency = Currency.objects.get(code=exchanged_currency_code)

            existing_rate = CurrencyExchangeRate.objects.filter(
                source_currency=source_currency,
                exchanged_currency=exchanged_currency,
                valuation_date=valuation_date
            ).first()

            if existing_rate:
                print(f"✅ Rate found in DB: {source_currency_code}/{exchanged_currency_code} on {valuation_date}")
                return existing_rate.rate_value

        except Currency.DoesNotExist:
            print(f"❌ Currency not found: {source_currency_code} or {exchanged_currency_code}")
            return None

        # Step 2: Rate not in DB, query providers with fallback
        print(f"🔍 Rate not in DB, querying providers for {source_currency_code}/{exchanged_currency_code} on {valuation_date}")

        providers = get_active_providers_ordered()

        if not providers:
            print("⚠️  No active providers configured")
            return None

        rate_value = None
        successful_provider = None

        # Step 3: Try each provider in priority order
        for provider in providers:
            provider_name = provider.__class__.__name__
            print(f"🔄 Trying {provider_name}...")

            rate_value = provider.get_exchange_rate_data(
                source_currency_code,
                exchanged_currency_code,
                valuation_date
            )

            if rate_value is not None:
                successful_provider = provider_name
                print(f"✅ {provider_name} returned rate: {rate_value}")
                break
            else:
                print(f"❌ {provider_name} failed, trying next...")

        # Step 4: Save to database if successful
        if rate_value is not None:
            try:
                CurrencyExchangeRate.objects.create(
                    source_currency=source_currency,
                    exchanged_currency=exchanged_currency,
                    valuation_date=valuation_date,
                    rate_value=rate_value
                )
                print(f"💾 Saved rate to DB (from {successful_provider})")
            except Exception as e:
                print(f"⚠️  Failed to save rate to DB: {e}")

        # Step 5: Return result
        if rate_value is None:
            print(f"❌ All providers failed for {source_currency_code}/{exchanged_currency_code} on {valuation_date}")

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

        Args:
            source_currency_code: Source currency
            exchanged_currency_code: Target currency
            amount: Amount to convert
            valuation_date: Date for the rate (defaults to today)

        Returns:
            Dict with conversion details, or None if conversion fails

        Example:
            >>> result = ExchangeRateService.convert_amount("USD", "EUR", Decimal("100"))
            >>> print(result)
            {
                "source_currency": "USD",
                "exchanged_currency": "EUR",
                "amount": Decimal("100"),
                "rate": Decimal("0.85"),
                "converted_amount": Decimal("85.00"),
                "valuation_date": date(2024, 1, 15)
            }
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
