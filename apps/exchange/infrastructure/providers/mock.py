"""
Mock provider for testing and fallback.
Generates random but realistic exchange rates.
"""

import random
from decimal import Decimal
from datetime import date

from apps.exchange.domain.interfaces import BaseExchangeRateProvider


class MockProvider(BaseExchangeRateProvider):
    """
    Mock provider that generates random exchange rates.
    Useful for:
    - Testing without external API calls
    - Fallback when all real providers fail
    - Development without API keys
    """

    # Base rates relative to USD (approximate real-world values)
    BASE_RATES = {
        "USD": Decimal("1.0"),
        "EUR": Decimal("0.85"),
        "GBP": Decimal("0.73"),
        "CHF": Decimal("0.88"),
    }

    def get_exchange_rate_data(
        self,
        source_currency: str,
        exchanged_currency: str,
        date: date
    ) -> Decimal | None:
        """
        Generate a mock exchange rate with small random variation.

        Args:
            source_currency: Base currency code
            exchanged_currency: Target currency code
            date: Date for the rate (used for seeding randomness)

        Returns:
            Mock exchange rate as Decimal
        """
        try:
            # Get base rates for both currencies (relative to USD)
            source_rate = self.BASE_RATES.get(source_currency)
            target_rate = self.BASE_RATES.get(exchanged_currency)

            if source_rate is None or target_rate is None:
                print(f"MockProvider: Unsupported currency pair {source_currency}/{exchanged_currency}")
                return None

            # Calculate cross rate
            base_rate = target_rate / source_rate

            # Add small random variation (±2%)
            # Use date as seed for reproducibility
            random.seed(f"{source_currency}{exchanged_currency}{date}")
            variation = Decimal(str(random.uniform(0.98, 1.02)))
            mock_rate = base_rate * variation

            # Round to 6 decimal places
            return mock_rate.quantize(Decimal("0.000001"))

        except Exception as e:
            print(f"Error in MockProvider: {e}")
            return None
