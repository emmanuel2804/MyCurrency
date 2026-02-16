import requests
from decimal import Decimal
from datetime import date

from core.settings import CURRENCY_BEACON_API_KEY, CURRENCY_BEACON_URL
from apps.exchange.domain.interfaces import BaseExchangeRateProvider


class CurrencyBeaconProvider(BaseExchangeRateProvider):
    """
    CurrencyBeacon API provider.
    Uses /historical endpoint to fetch exchange rates for a specific date.
    """

    def get_exchange_rate_data(
        self,
        source_currency: str,
        exchanged_currency: str,
        date: date
    ) -> Decimal | None:
        """
        Fetch historical exchange rate from CurrencyBeacon API.

        Args:
            source_currency: Base currency code (e.g. USD)
            exchanged_currency: Target currency code (e.g. EUR)
            date: Date for the exchange rate

        Returns:
            Exchange rate as Decimal, or None if error occurs
        """
        # Format: https://api.currencybeacon.com/v1/historical?api_key=KEY&base=USD&date=2024-01-15&symbols=EUR
        date_str = date.strftime("%Y-%m-%d")
        url = (
            f"{CURRENCY_BEACON_URL}/historical"
            f"?api_key={CURRENCY_BEACON_API_KEY}"
            f"&base={source_currency}"
            f"&date={date_str}"
            f"&symbols={exchanged_currency}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Response format: {"response": {"rates": {"EUR": 0.85}}}
            rate = data['response']['rates'][exchanged_currency]
            return Decimal(str(rate))

        except requests.exceptions.Timeout:
            print(f"Timeout calling CurrencyBeacon API for {source_currency}/{exchanged_currency} on {date_str}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error from CurrencyBeacon: {e}")
            return None
        except (KeyError, ValueError) as e:
            print(f"Invalid response from CurrencyBeacon: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error calling CurrencyBeacon: {e}")
            return None