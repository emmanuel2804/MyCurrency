"""
Data Transfer Objects for the application layer.
DTOs decouple internal domain models from external API contracts.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional


@dataclass
class CurrencyDTO:
    """Currency data transfer object."""
    code: str
    name: str
    symbol: str
    id: Optional[str] = None


@dataclass
class ExchangeRateDTO:
    """Exchange rate data transfer object."""
    source_currency_code: str
    exchanged_currency_code: str
    rate_value: Decimal
    valuation_date: date
    id: Optional[str] = None


@dataclass
class ConversionRequestDTO:
    """Request DTO for currency conversion."""
    source_currency: str
    exchanged_currency: str
    amount: Decimal
    valuation_date: Optional[date] = None


@dataclass
class ConversionResultDTO:
    """Result DTO for currency conversion."""
    source_currency: str
    exchanged_currency: str
    amount: Decimal
    rate: Decimal
    converted_amount: Decimal
    valuation_date: date


@dataclass
class TimeSeriesRequestDTO:
    """Request DTO for time series data."""
    source_currency: str
    date_from: date
    date_to: date


@dataclass
class TimeSeriesDataPoint:
    """Single data point in time series."""
    date: date
    exchanged_currency: str
    rate: Decimal


@dataclass
class TimeSeriesResultDTO:
    """Result DTO for time series data."""
    source_currency: str
    date_from: date
    date_to: date
    data_points: List[TimeSeriesDataPoint]


@dataclass
class ProviderDTO:
    """Provider data transfer object."""
    name: str
    priority: int
    is_active: bool
    display_name: str
    id: Optional[str] = None


@dataclass
class RateSyncResultDTO:
    """Result DTO for rate synchronization task."""
    success: bool
    rates_synced: int
    currencies_processed: List[str]
    errors: List[str]
    provider_used: Optional[str] = None
