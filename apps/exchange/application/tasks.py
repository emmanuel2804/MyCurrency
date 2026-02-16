"""
Celery tasks for background processing.
Tasks handle asynchronous operations like rate synchronization and cleanup.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict

from celery import shared_task
from django.utils import timezone

from apps.exchange.infrastructure.persistence.repositories import (
    CurrencyRepository,
    CurrencyExchangeRateRepository,
    ProviderRepository,
)
from apps.exchange.infrastructure.providers.registry import get_provider_instance


@shared_task(name="sync_exchange_rates_for_today")
def sync_exchange_rates_for_today() -> Dict:
    """
    Sync exchange rates for all currency pairs for today.

    This task:
    1. Gets all active currencies
    2. For each currency pair, fetches the rate from active providers
    3. Saves rates to database

    Returns:
        Dict with sync results (success count, errors, etc.)
    """
    print("🔄 Starting exchange rate synchronization for today...")

    today = date.today()
    currencies = CurrencyRepository.get_all_active()

    if not currencies:
        return {
            "success": False,
            "message": "No currencies found in database",
            "rates_synced": 0,
            "errors": []
        }

    providers = ProviderRepository.get_active_ordered()

    if not providers:
        return {
            "success": False,
            "message": "No active providers configured",
            "rates_synced": 0,
            "errors": []
        }

    rates_synced = 0
    errors = []
    currency_pairs_processed = []

    # Generate all currency pairs (avoiding duplicates and self-pairs)
    for i, source_currency in enumerate(currencies):
        for exchanged_currency in currencies[i+1:]:
            # Check both directions (USD->EUR and EUR->USD)
            for src, tgt in [(source_currency, exchanged_currency), (exchanged_currency, source_currency)]:
                pair_key = f"{src.code}/{tgt.code}"

                # Check if rate already exists
                existing_rate = CurrencyExchangeRateRepository.get_rate(
                    src, tgt, today
                )

                if existing_rate:
                    print(f"✅ Rate already exists: {pair_key}")
                    continue

                # Try to fetch rate from providers
                rate_value = None
                provider_used = None

                for provider_model in providers:
                    provider_instance = get_provider_instance(provider_model.name)
                    if not provider_instance:
                        continue

                    try:
                        rate_value = provider_instance.get_exchange_rate_data(
                            src.code,
                            tgt.code,
                            today
                        )

                        if rate_value:
                            provider_used = provider_model.name
                            break
                    except Exception as e:
                        errors.append(f"{pair_key} from {provider_model.name}: {str(e)}")

                # Save rate if found
                if rate_value:
                    try:
                        CurrencyExchangeRateRepository.create(
                            source_currency=src,
                            exchanged_currency=tgt,
                            valuation_date=today,
                            rate_value=rate_value
                        )
                        rates_synced += 1
                        currency_pairs_processed.append(pair_key)
                        print(f"✅ Synced {pair_key}: {rate_value} (from {provider_used})")
                    except Exception as e:
                        errors.append(f"Failed to save {pair_key}: {str(e)}")
                else:
                    errors.append(f"No provider returned rate for {pair_key}")

    return {
        "success": True,
        "rates_synced": rates_synced,
        "currency_pairs_processed": currency_pairs_processed,
        "errors": errors,
        "date": today.isoformat()
    }


@shared_task(name="sync_exchange_rates_for_date_range")
def sync_exchange_rates_for_date_range(
    date_from_str: str,
    date_to_str: str
) -> Dict:
    """
    Sync exchange rates for a date range (backfill historical data).

    Args:
        date_from_str: Start date in YYYY-MM-DD format
        date_to_str: End date in YYYY-MM-DD format

    Returns:
        Dict with sync results
    """
    print(f"🔄 Starting rate sync for range {date_from_str} to {date_to_str}...")

    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError as e:
        return {
            "success": False,
            "message": f"Invalid date format: {str(e)}",
            "rates_synced": 0
        }

    if date_from > date_to:
        return {
            "success": False,
            "message": "date_from must be before date_to",
            "rates_synced": 0
        }

    total_synced = 0
    current_date = date_from

    while current_date <= date_to:
        print(f"📅 Processing {current_date}...")
        # Temporarily override today's date for the sync task
        # In production, you'd modify sync_exchange_rates_for_today to accept a date parameter
        # For now, we'll call a date-specific version

        # TODO: Implement date-specific sync or refactor sync_exchange_rates_for_today
        # to accept date parameter

        current_date += timedelta(days=1)

    return {
        "success": True,
        "rates_synced": total_synced,
        "date_from": date_from_str,
        "date_to": date_to_str
    }


@shared_task(name="cleanup_old_exchange_rates")
def cleanup_old_exchange_rates(days_to_keep: int = 90) -> Dict:
    """
    Clean up exchange rates older than specified days.

    Args:
        days_to_keep: Number of days of history to keep (default: 90)

    Returns:
        Dict with cleanup results
    """
    print(f"🧹 Cleaning up rates older than {days_to_keep} days...")

    try:
        deleted_count = CurrencyExchangeRateRepository.delete_older_than(days_to_keep)

        return {
            "success": True,
            "rates_deleted": deleted_count,
            "days_kept": days_to_keep,
            "cutoff_date": (timezone.now().date() - timedelta(days=days_to_keep)).isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Cleanup failed: {str(e)}",
            "rates_deleted": 0
        }


@shared_task(name="check_providers_health")
def check_providers_health() -> Dict:
    """
    Check health of all configured providers.

    Tests each provider by fetching a sample rate (USD->EUR for today).

    Returns:
        Dict with health check results for each provider
    """
    print("🏥 Checking provider health...")

    providers = ProviderRepository.get_all()
    today = date.today()

    results = {}

    for provider_model in providers:
        provider_instance = get_provider_instance(provider_model.name)

        if not provider_instance:
            results[provider_model.name] = {
                "status": "error",
                "message": "Provider not found in registry",
                "is_active": provider_model.is_active
            }
            continue

        try:
            # Test with USD->EUR
            test_rate = provider_instance.get_exchange_rate_data("USD", "EUR", today)

            if test_rate:
                results[provider_model.name] = {
                    "status": "healthy",
                    "test_rate": str(test_rate),
                    "is_active": provider_model.is_active,
                    "priority": provider_model.priority
                }
            else:
                results[provider_model.name] = {
                    "status": "unhealthy",
                    "message": "Provider returned None",
                    "is_active": provider_model.is_active
                }
        except Exception as e:
            results[provider_model.name] = {
                "status": "error",
                "message": str(e),
                "is_active": provider_model.is_active
            }

    return {
        "success": True,
        "providers_checked": len(results),
        "results": results,
        "timestamp": timezone.now().isoformat()
    }


@shared_task(name="sync_missing_rates_for_currency_pair")
def sync_missing_rates_for_currency_pair(
    source_currency_code: str,
    exchanged_currency_code: str,
    date_from_str: str,
    date_to_str: str
) -> Dict:
    """
    Sync missing rates for a specific currency pair within a date range.

    Useful for filling gaps in historical data.

    Args:
        source_currency_code: Source currency code (e.g., "USD")
        exchanged_currency_code: Target currency code (e.g., "EUR")
        date_from_str: Start date in YYYY-MM-DD format
        date_to_str: End date in YYYY-MM-DD format

    Returns:
        Dict with sync results
    """
    print(f"🔄 Syncing {source_currency_code}/{exchanged_currency_code} from {date_from_str} to {date_to_str}...")

    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError as e:
        return {
            "success": False,
            "message": f"Invalid date format: {str(e)}"
        }

    source_currency = CurrencyRepository.get_by_code(source_currency_code)
    exchanged_currency = CurrencyRepository.get_by_code(exchanged_currency_code)

    if not source_currency or not exchanged_currency:
        return {
            "success": False,
            "message": f"Currency not found: {source_currency_code} or {exchanged_currency_code}"
        }

    providers = ProviderRepository.get_active_ordered()
    rates_synced = 0
    errors = []

    current_date = date_from
    while current_date <= date_to:
        # Check if rate exists
        existing_rate = CurrencyExchangeRateRepository.get_rate(
            source_currency,
            exchanged_currency,
            current_date
        )

        if not existing_rate:
            # Try to fetch from providers
            rate_value = None
            for provider_model in providers:
                provider_instance = get_provider_instance(provider_model.name)
                if provider_instance:
                    try:
                        rate_value = provider_instance.get_exchange_rate_data(
                            source_currency_code,
                            exchanged_currency_code,
                            current_date
                        )
                        if rate_value:
                            break
                    except Exception as e:
                        errors.append(f"{current_date}: {str(e)}")

            if rate_value:
                try:
                    CurrencyExchangeRateRepository.create(
                        source_currency=source_currency,
                        exchanged_currency=exchanged_currency,
                        valuation_date=current_date,
                        rate_value=rate_value
                    )
                    rates_synced += 1
                except Exception as e:
                    errors.append(f"Failed to save rate for {current_date}: {str(e)}")

        current_date += timedelta(days=1)

    return {
        "success": True,
        "rates_synced": rates_synced,
        "currency_pair": f"{source_currency_code}/{exchanged_currency_code}",
        "errors": errors
    }
