import requests
from decimal import Decimal
from datetime import date

from core.settings import CURRENCY_BEACON_API_KEY, CURRENCY_BEACON_URL
from apps.exchange.domain.interfaces import BaseExchangeRateProvider


class CurrencyBeaconProvider(BaseExchangeRateProvider):
    def get_exchange_rate_data(
        self, 
        source_currency: str, 
        exchanged_currency: str, 
        date: date
    ) -> Decimal | None:
        # curl -X GET "https://api.currencybeacon.com/v1/convert?api_key=YOUR_KEY&from=USD&to=GBP&amount=1"
        url = f"{CURRENCY_BEACON_URL}/convert?api_key={CURRENCY_BEACON_API_KEY}&from={source_currency}&to={exchanged_currency}&amount=1"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return Decimal(str(data['response']['value']))
        except Exception as e:
            print(f"Error getting exchange rate from Currency Beacon: {e}")
            return None