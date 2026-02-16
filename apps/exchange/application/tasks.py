"""
Celery tasks for background processing.
"""

import asyncio
import aiohttp
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, cast

from celery import shared_task

from apps.exchange.infrastructure.persistence.repositories import CurrencyRepository
from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
)
from core.settings import CURRENCY_BEACON_API_KEY, CURRENCY_BEACON_URL


async def fetch_rate_async(
    session: aiohttp.ClientSession,
    source_code: str,
    target_code: str,
    valuation_date: date
) -> Optional[Tuple[str, str, date, Decimal]]:
    """
    Fetch exchange rate asynchronously using aiohttp.

    Returns tuple: (source_code, target_code, date, rate) or None if failed
    """
    date_str = valuation_date.strftime("%Y-%m-%d")
    url = (
        f"{CURRENCY_BEACON_URL}/historical"
        f"?api_key={CURRENCY_BEACON_API_KEY}"
        f"&base={source_code}"
        f"&date={date_str}"
        f"&symbols={target_code}"
    )

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            data = await response.json()
            rate = data['response']['rates'][target_code]
            return (source_code, target_code, valuation_date, Decimal(str(rate)))
    except Exception as e:
        print(f"Error fetching {source_code}/{target_code} for {date_str}: {e}")
        return None


async def fetch_rates_for_date(
    currencies: List[Currency],
    valuation_date: date
) -> List[Tuple[str, str, date, Decimal]]:
    """
    Fetch all currency pair rates for a specific date using concurrent requests.

    This uses asyncio to make I/O-bound operations concurrent, maximizing throughput.
    """
    tasks = []

    async with aiohttp.ClientSession() as session:
        for i, source_currency in enumerate(currencies):
            for exchanged_currency in currencies[i+1:]:
                for src, tgt in [(source_currency, exchanged_currency), (exchanged_currency, source_currency)]:
                    task = fetch_rate_async(session, src.code, tgt.code, valuation_date)
                    tasks.append(task)

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

    This task uses asyncio/aiohttp for concurrent HTTP requests (not parallel processing)
    because the bottleneck is I/O (network requests), not CPU.

    Bulk creates database records for efficiency.

    Args:
        date_from_str: Start date in YYYY-MM-DD format
        date_to_str: End date in YYYY-MM-DD format

    Returns:
        Dict with operation results
    """
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
            results = asyncio.run(fetch_rates_for_date(currencies, current_date))

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
