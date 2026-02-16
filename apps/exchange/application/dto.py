"""
Data Transfer Objects for the application layer.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class CurrencyDTO:
    code: str
    name: str
    symbol: str
    id: Optional[str] = None


@dataclass
class ExchangeRateDTO:
    source_currency_code: str
    exchanged_currency_code: str
    rate_value: Decimal
    valuation_date: date
    id: Optional[str] = None


@dataclass
class ConversionResultDTO:
    source_currency: str
    exchanged_currency: str
    amount: Decimal
    rate: Decimal
    converted_amount: Decimal
    valuation_date: date
