from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.exchange.api.v1.views import (
    CurrencyExchangeRateViewSet,
    CurrencyViewSet,
    ProviderViewSet,
)

router = DefaultRouter()
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'rates', CurrencyExchangeRateViewSet, basename='exchange-rate')
router.register(r'providers', ProviderViewSet, basename='provider')

urlpatterns = [
    path('', include(router.urls)),
]