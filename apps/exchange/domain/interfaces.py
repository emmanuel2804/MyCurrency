from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import date


class BaseExchangeRateProvider(ABC):
    @abstractmethod
    def get_exchange_rate_data(self, source_currency: str, exchanged_currency: str, date: date) -> Decimal | None:
        pass
