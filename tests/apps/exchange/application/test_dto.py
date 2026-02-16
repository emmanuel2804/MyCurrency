import pytest
from decimal import Decimal
from datetime import date

from apps.exchange.application.dto import (
    CurrencyDTO,
    ExchangeRateDTO,
    ConversionRequestDTO,
    ConversionResultDTO,
    TimeSeriesRequestDTO,
    TimeSeriesDataPoint,
    TimeSeriesResultDTO,
    ProviderDTO,
    RateSyncResultDTO
)


class TestDataTransferObjects:
    """Tests for DTOs - mainly structure validation."""

    def test_currency_dto(self):
        """Test CurrencyDTO structure."""
        dto = CurrencyDTO(
            code="USD",
            name="US Dollar",
            symbol="$",
            id="123"
        )

        assert dto.code == "USD"
        assert dto.name == "US Dollar"
        assert dto.symbol == "$"
        assert dto.id == "123"

    def test_currency_dto_optional_id(self):
        """Test CurrencyDTO with optional id."""
        dto = CurrencyDTO(
            code="USD",
            name="US Dollar",
            symbol="$"
        )

        assert dto.id is None

    def test_exchange_rate_dto(self):
        """Test ExchangeRateDTO structure."""
        dto = ExchangeRateDTO(
            source_currency_code="USD",
            exchanged_currency_code="EUR",
            rate_value=Decimal("0.85"),
            valuation_date=date(2024, 5, 21)
        )

        assert dto.source_currency_code == "USD"
        assert dto.exchanged_currency_code == "EUR"
        assert dto.rate_value == Decimal("0.85")
        assert dto.valuation_date == date(2024, 5, 21)

    def test_conversion_request_dto(self):
        """Test ConversionRequestDTO structure."""
        dto = ConversionRequestDTO(
            source_currency="USD",
            exchanged_currency="EUR",
            amount=Decimal("100"),
            valuation_date=date(2024, 5, 21)
        )

        assert dto.source_currency == "USD"
        assert dto.exchanged_currency == "EUR"
        assert dto.amount == Decimal("100")
        assert dto.valuation_date == date(2024, 5, 21)

    def test_conversion_request_dto_optional_date(self):
        """Test ConversionRequestDTO with optional valuation_date."""
        dto = ConversionRequestDTO(
            source_currency="USD",
            exchanged_currency="EUR",
            amount=Decimal("100")
        )

        assert dto.valuation_date is None

    def test_conversion_result_dto(self):
        """Test ConversionResultDTO structure."""
        dto = ConversionResultDTO(
            source_currency="USD",
            exchanged_currency="EUR",
            amount=Decimal("100"),
            rate=Decimal("0.85"),
            converted_amount=Decimal("85"),
            valuation_date=date(2024, 5, 21)
        )

        assert dto.source_currency == "USD"
        assert dto.exchanged_currency == "EUR"
        assert dto.amount == Decimal("100")
        assert dto.rate == Decimal("0.85")
        assert dto.converted_amount == Decimal("85")

    def test_time_series_request_dto(self):
        """Test TimeSeriesRequestDTO structure."""
        dto = TimeSeriesRequestDTO(
            source_currency="USD",
            date_from=date(2024, 5, 1),
            date_to=date(2024, 5, 31)
        )

        assert dto.source_currency == "USD"
        assert dto.date_from == date(2024, 5, 1)
        assert dto.date_to == date(2024, 5, 31)

    def test_time_series_data_point(self):
        """Test TimeSeriesDataPoint structure."""
        dto = TimeSeriesDataPoint(
            date=date(2024, 5, 21),
            exchanged_currency="EUR",
            rate=Decimal("0.85")
        )

        assert dto.date == date(2024, 5, 21)
        assert dto.exchanged_currency == "EUR"
        assert dto.rate == Decimal("0.85")

    def test_time_series_result_dto(self):
        """Test TimeSeriesResultDTO structure."""
        data_points = [
            TimeSeriesDataPoint(
                date=date(2024, 5, 21),
                exchanged_currency="EUR",
                rate=Decimal("0.85")
            )
        ]

        dto = TimeSeriesResultDTO(
            source_currency="USD",
            date_from=date(2024, 5, 1),
            date_to=date(2024, 5, 31),
            data_points=data_points
        )

        assert dto.source_currency == "USD"
        assert len(dto.data_points) == 1
        assert dto.data_points[0].rate == Decimal("0.85")

    def test_provider_dto(self):
        """Test ProviderDTO structure."""
        dto = ProviderDTO(
            name="mock",
            priority=1,
            is_active=True,
            display_name="Mock Provider",
            id="123"
        )

        assert dto.name == "mock"
        assert dto.priority == 1
        assert dto.is_active is True
        assert dto.display_name == "Mock Provider"

    def test_rate_sync_result_dto(self):
        """Test RateSyncResultDTO structure."""
        dto = RateSyncResultDTO(
            success=True,
            rates_synced=10,
            currencies_processed=["USD", "EUR"],
            errors=[],
            provider_used="mock"
        )

        assert dto.success is True
        assert dto.rates_synced == 10
        assert len(dto.currencies_processed) == 2
        assert dto.provider_used == "mock"

    def test_rate_sync_result_dto_with_errors(self):
        """Test RateSyncResultDTO with errors."""
        dto = RateSyncResultDTO(
            success=False,
            rates_synced=5,
            currencies_processed=["USD"],
            errors=["Provider timeout", "Invalid response"]
        )

        assert dto.success is False
        assert len(dto.errors) == 2
        assert dto.provider_used is None
