from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import render
from decimal import Decimal
from datetime import date
from typing import Any

from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
)
from apps.exchange.domain.services import ExchangeRateService


class ExchangeAdminSite(AdminSite):
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        app_list.append({
            'name': 'Tools',
            'app_label': 'tools',
            'app_url': '#',
            'has_module_perms': True,
            'models': [{
                'name': 'Currency Converter',
                'object_name': 'CurrencyConverter',
                'admin_url': '/admin/converter/',
                'view_only': True,
                'add_url': None,
                'perms': {'add': False, 'change': False, 'delete': False, 'view': True},
            }],
        })
        return app_list

    def get_urls(self):  # type: ignore[override]
        return [
            path(
                'converter/',
                self.admin_view(self.converter_view),
                name='exchange_converter'
            ),
        ] + super().get_urls()

    def converter_view(self, request: Any) -> Any:
        context = {
            **self.each_context(request),
            'title': 'Currency Converter',
            'subtitle': 'Convert amounts between currencies',
            'currencies': Currency.objects.all().order_by('code'),
            'results': None,
            'form_data': None,
        }

        if request.method == 'POST':
            source_code = request.POST.get('source_currency')
            amount_str = request.POST.get('amount', '0')
            target_codes = request.POST.getlist('target_currencies')
            date_str = request.POST.get('valuation_date')

            try:
                amount = Decimal(amount_str)
            except:
                amount = Decimal('0')

            try:
                valuation_date = date.fromisoformat(date_str) if date_str else date.today()
            except:
                valuation_date = date.today()

            context['form_data'] = {
                'source_currency': source_code,
                'amount': amount_str,
                'target_currencies': target_codes,
                'valuation_date': date_str or date.today().isoformat()
            }

            if source_code and target_codes and amount > 0:
                results = []
                for target_code in target_codes:
                    result = ExchangeRateService.convert_amount(
                        source_code,
                        target_code,
                        amount,
                        valuation_date
                    )

                    if result:
                        results.append({
                            'source': result['source_currency'],
                            'target': result['exchanged_currency'],
                            'rate': result['rate'],
                            'converted_amount': result['converted_amount'],
                            'date': result['valuation_date']
                        })
                    else:
                        results.append({
                            'source': source_code,
                            'target': target_code,
                            'error': True
                        })

                context['results'] = results

        return render(request, 'admin/exchange/converter.html', context)


admin_site = ExchangeAdminSite(name='admin')


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('code', 'name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('code',)


class CurrencyExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('get_currency_pair', 'rate_value', 'valuation_date', 'created_at')
    list_filter = ('valuation_date', 'source_currency', 'exchanged_currency')
    search_fields = ('source_currency__code', 'exchanged_currency__code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'valuation_date'
    ordering = ('-valuation_date', 'source_currency__code')

    def get_currency_pair(self, obj: CurrencyExchangeRate) -> str:
        return f"{obj.source_currency.code}/{obj.exchanged_currency.code}"
    get_currency_pair.short_description = 'Currency Pair'  # type: ignore


class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'is_active', 'created_at')
    list_filter = ('is_active', 'name')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('priority',)


admin_site.register(Currency, CurrencyAdmin)
admin_site.register(CurrencyExchangeRate, CurrencyExchangeRateAdmin)
admin_site.register(Provider, ProviderAdmin)
