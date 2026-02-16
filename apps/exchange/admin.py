"""
Django Admin configuration for Exchange app.
Includes custom admin interfaces and a currency converter view.
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from decimal import Decimal
from datetime import date

from apps.exchange.infrastructure.persistence.models import (
    Currency,
    CurrencyExchangeRate,
    Provider,
)
from apps.exchange.domain.services import ExchangeRateService


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    """Admin interface for Currency model."""

    list_display = ('code', 'name', 'symbol', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('code', 'name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('code',)

    fieldsets = (
        ('Currency Information', {
            'fields': ('code', 'name', 'symbol')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CurrencyExchangeRate)
class CurrencyExchangeRateAdmin(admin.ModelAdmin):
    """Admin interface for CurrencyExchangeRate model."""

    list_display = (
        'get_currency_pair',
        'rate_value',
        'valuation_date',
        'created_at'
    )
    list_filter = (
        'valuation_date',
        'source_currency',
        'exchanged_currency',
    )
    search_fields = (
        'source_currency__code',
        'exchanged_currency__code',
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'valuation_date'
    ordering = ('-valuation_date', 'source_currency__code')

    fieldsets = (
        ('Exchange Rate', {
            'fields': (
                'source_currency',
                'exchanged_currency',
                'rate_value',
                'valuation_date'
            )
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_currency_pair(self, obj):
        """Display currency pair in format SOURCE/TARGET."""
        return f"{obj.source_currency.code}/{obj.exchanged_currency.code}"
    get_currency_pair.short_description = 'Currency Pair'
    get_currency_pair.admin_order_field = 'source_currency__code'


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin interface for Provider model with priority management."""

    list_display = (
        'get_name_display',
        'priority',
        'get_status',
        'created_at'
    )
    list_filter = ('is_active', 'name')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('priority',)
    actions = ['activate_providers', 'deactivate_providers']

    fieldsets = (
        ('Provider Configuration', {
            'fields': ('name', 'priority', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_name_display(self, obj):
        """Display provider name with icon."""
        icons = {
            'currency_beacon': '🌐',
            'mock': '🎭'
        }
        icon = icons.get(obj.name, '📡')
        return f"{icon} {obj.get_name_display()}"
    get_name_display.short_description = 'Provider'

    def get_status(self, obj):
        """Display status with colored indicator."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: red;">○ Inactive</span>'
        )
    get_status.short_description = 'Status'

    @admin.action(description='✅ Activate selected providers')
    def activate_providers(self, request, queryset):
        """Bulk action to activate providers."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} provider(s) activated successfully.'
        )

    @admin.action(description='🚫 Deactivate selected providers')
    def deactivate_providers(self, request, queryset):
        """Bulk action to deactivate providers."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} provider(s) deactivated successfully.'
        )


class CurrencyConverterAdmin:
    """
    Custom admin view for currency conversion.

    Accessible at /admin/exchange/converter/
    Allows converting amounts between currencies using the fallback mechanism.
    """

    def get_urls(self):
        """Register custom URLs for converter view."""
        return [
            path(
                'converter/',
                self.admin_site.admin_view(self.converter_view),
                name='exchange_converter'
            ),
        ]

    def converter_view(self, request):
        """
        Currency converter view.

        GET: Display form
        POST: Process conversion and display results
        """
        context = {
            **self.admin_site.each_context(request),
            'title': 'Currency Converter',
            'subtitle': 'Convert amounts between currencies',
            'currencies': Currency.objects.all().order_by('code'),
            'results': None,
            'form_data': None,
        }

        if request.method == 'POST':
            source_currency_code = request.POST.get('source_currency')
            amount_str = request.POST.get('amount', '0')
            target_currencies = request.POST.getlist('target_currencies')
            valuation_date_str = request.POST.get('valuation_date')

            # Parse inputs
            try:
                amount = Decimal(amount_str)
            except:
                amount = Decimal('0')

            if valuation_date_str:
                try:
                    valuation_date = date.fromisoformat(valuation_date_str)
                except:
                    valuation_date = date.today()
            else:
                valuation_date = date.today()

            # Store form data to repopulate
            context['form_data'] = {
                'source_currency': source_currency_code,
                'amount': amount_str,
                'target_currencies': target_currencies,
                'valuation_date': valuation_date_str or date.today().isoformat()
            }

            # Perform conversions
            if source_currency_code and target_currencies and amount > 0:
                results = []
                for target_code in target_currencies:
                    result = ExchangeRateService.convert_amount(
                        source_currency_code,
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
                            'source': source_currency_code,
                            'target': target_code,
                            'rate': None,
                            'converted_amount': None,
                            'error': True
                        })

                context['results'] = results

        return render(request, 'admin/exchange/converter.html', context)


# Register converter view
# Access at: /admin/exchange/converter/
converter_admin = CurrencyConverterAdmin()
converter_admin.admin_site = admin.site

admin.site.get_urls = (
    lambda original: lambda: original() + converter_admin.get_urls()
)(admin.site.get_urls)
