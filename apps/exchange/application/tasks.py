"""
Celery tasks for background processing.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, cast

from celery import shared_task

from apps.exchange.infrastructure.persistence.repositories import CurrencyRepository
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
)
from apps.exchange.infrastructure.providers.registry import PROVIDER_REGISTRY
from apps.exchange.domain.interfaces import BaseExchangeRateProvider


def get_top_priority_provider() -> Optional[BaseExchangeRateProvider]:
    """
    Returns an instance of the active provider with the highest priority (lowest number).
    Returns None if no active provider is found or registered.
    """
    provider_model = Provider.objects.filter(is_active=True).order_by('priority').first()

    if provider_model is None:
        return None

    provider_class = PROVIDER_REGISTRY.get(provider_model.name)
    if provider_class is None:
        return None

    return provider_class()


async def fetch_rate_async(
    provider: BaseExchangeRateProvider,
    source_code: str,
    target_code: str,
    valuation_date: date
) -> Optional[Tuple[str, str, date, Decimal]]:
    """
    Fetch exchange rate asynchronously by running the synchronous provider
    in a thread pool via asyncio.to_thread.

    Returns tuple: (source_code, target_code, date, rate) or None if failed.
    """
    rate = await asyncio.to_thread(
        provider.get_exchange_rate_data,
        source_code,
        target_code,
        valuation_date
    )

    if rate is None:
        print(f"No rate for {source_code}/{target_code} on {valuation_date}")
        return None

    return (source_code, target_code, valuation_date, rate)


async def fetch_rates_for_date(
    provider: BaseExchangeRateProvider,
    currencies: List[Currency],
    valuation_date: date
) -> List[Tuple[str, str, date, Decimal]]:
    """
    Fetch all currency pair rates for a specific date using concurrent requests.

    Uses asyncio to make I/O-bound operations concurrent, maximizing throughput.
    """
    tasks = []

    for i, source_currency in enumerate(currencies):
        for exchanged_currency in currencies[i+1:]:
            for src, tgt in [(source_currency, exchanged_currency), (exchanged_currency, source_currency)]:
                tasks.append(fetch_rate_async(provider, src.code, tgt.code, valuation_date))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results: List[Tuple[str, str, date, Decimal]] = []
    for r in results:
        if r is not None and not isinstance(r, Exception):
            valid_results.append(cast(Tuple[str, str, date, Decimal], r))

    return valid_results


@shared_task(name="load_historical_data")
def load_historical_data(date_from_str: str, date_to_str: str) -> Dict:
    """
    Load historical exchange rate data for a date range using concurrent I/O.

    Uses the active provider with the highest priority. If that provider fails,
    the task fails — no fallback mechanism.

    Args:
        date_from_str: Start date in YYYY-MM-DD format
        date_to_str: End date in YYYY-MM-DD format

    Returns:
        Dict with operation results
    """
    provider = get_top_priority_provider()
    if provider is None:
        return {
            "success": False,
            "message": "No active provider found. Check that at least one provider is active in the database.",
            "rates_loaded": 0
        }

    print(f"Using provider: {provider.__class__.__name__}")
    print(f"Loading historical data from {date_from_str} to {date_to_str}...")

    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError as e:
        return {
            "success": False,
            "message": f"Invalid date format: {str(e)}",
            "rates_loaded": 0
        }

    if date_from > date_to:
        return {
            "success": False,
            "message": "date_from must be before or equal to date_to",
            "rates_loaded": 0
        }

    currencies = CurrencyRepository.get_all_active()
    if not currencies:
        return {
            "success": False,
            "message": "No currencies found in database",
            "rates_loaded": 0
        }

    print(f"Processing {len(currencies)} currencies for {(date_to - date_from).days + 1} days...")

    total_rates_loaded = 0
    errors = []
    current_date = date_from

    while current_date <= date_to:
        print(f"Processing {current_date}...")

        try:
            results = asyncio.run(fetch_rates_for_date(provider, currencies, current_date))

            if not results:
                errors.append(f"No rates fetched for {current_date}")
                current_date += timedelta(days=1)
                continue

            rates_to_create = []
            for source_code, target_code, val_date, rate_value in results:
                source_currency = next((c for c in currencies if c.code == source_code), None)
                target_currency = next((c for c in currencies if c.code == target_code), None)

                if source_currency and target_currency:
                    existing = CurrencyExchangeRate.objects.filter(
                        source_currency=source_currency,
                        exchanged_currency=target_currency,
                        valuation_date=val_date
                    ).first()

                    if not existing:
                        rates_to_create.append(
                            CurrencyExchangeRate(
                                source_currency=source_currency,
                                exchanged_currency=target_currency,
                                valuation_date=val_date,
                                rate_value=rate_value
                            )
                        )

            if rates_to_create:
                CurrencyExchangeRate.objects.bulk_create(
                    rates_to_create,
                    ignore_conflicts=True
                )
                total_rates_loaded += len(rates_to_create)
                print(f"Created {len(rates_to_create)} rates for {current_date}")

        except Exception as e:
            errors.append(f"Error processing {current_date}: {str(e)}")
            print(f"Error on {current_date}: {e}")

        current_date += timedelta(days=1)

    return {
        "success": True,
        "rates_loaded": total_rates_loaded,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "errors": errors
    }
