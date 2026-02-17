from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.exchange.api.v2.views import ExchangeRateV2ViewSet

router = DefaultRouter()
router.register(r'rates', ExchangeRateV2ViewSet, basename='exchange-rate-v2')

urlpatterns = [
    path('', include(router.urls)),
]
