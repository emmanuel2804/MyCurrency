"""
Pure domain entities (POPOs).
No dependency on Django or the ORM.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4, UUID


@dataclass(frozen=True)
class CurrencyDTO:

    id: UUID = field(default_factory=uuid4)
    code: str
    name: str
    symbol: str

    def __post_init__(self):
        if len(self.code) != 3:
            raise ValueError(f"Currency code must be exactly 3 characters, got '{self.code}'")


@dataclass(frozen=True)
class ExchangeRate:

    source_currency: str
    exchanged_currency: str
    valuation_date: date
    rate_value: Decimal
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        if self.rate_value <= 0:
            raise ValueError(f"rate_value must be positive, got {self.rate_value}")
        if self.source_currency == self.exchanged_currency:
            raise ValueError("source_currency and exchanged_currency must be different")

    def convert(self, amount: Decimal) -> Decimal:
        return (amount * self.rate_value).quantize(Decimal("0.000001"))