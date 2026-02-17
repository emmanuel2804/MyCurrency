import requests
from decimal import Decimal
from datetime import date

from core.settings import EXCHANGERATE_API_KEY, EXCHANGERATE_URL
from apps.exchange.domain.interfaces import BaseExchangeRateProvider


class ExchangeRateProvider(BaseExchangeRateProvider):
    """
    ExchangeRate API provider.
    Uses /historical endpoint to fetch exchange rates for a specific date.
    """

    def get_exchange_rate_data(
        self,
        source_currency: str,
        exchanged_currency: str,
        date: date
    ) -> Decimal | None:
        """
        Fetch historical exchange rate from ExchangeRate API.

        Args:
            source_currency: Base currency code (e.g. USD)
            exchanged_currency: Target currency code (e.g. EUR)
            date: Date for the exchange rate

        Returns:
            Exchange rate as Decimal, or None if error occurs
        """

        # if EXCHANGERATE_URL is not configured, return None
        if not EXCHANGERATE_URL or not EXCHANGERATE_API_KEY:
            print("EXCHANGERATE_URL or EXCHANGERATE_API_KEY is not configured. Cannot fetch exchange rates.")
            return None
        
        # Format: https://v6.exchangerate-api.com/v6/YOUR-API-KEY/history/USD/YEAR/MONTH/DAY
        date_str = date.strftime("%Y-%m-%d")
        url = (
            f"{EXCHANGERATE_URL}/{EXCHANGERATE_API_KEY}/pair/{source_currency}/{exchanged_currency}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Response format: {"response": {"rates": {"EUR": 0.85}}}
            rate = data['conversion_rate']
            return Decimal(str(rate))

        except requests.exceptions.Timeout:
            print(f"Timeout calling ExchangeRate API for {source_currency}/{exchanged_currency} on {date_str}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error from ExchangeRate API: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Invalid response from ExchangeRate API: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error calling ExchangeRate API: {e}")
            return None