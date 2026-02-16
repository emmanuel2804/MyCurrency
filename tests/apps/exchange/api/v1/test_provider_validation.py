import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.exchange.infrastructure.persistence.models import Provider, ProviderName


@pytest.mark.django_db(transaction=True)
class TestProviderPriorityValidation:
    """Tests for provider priority duplicate validation."""

    def setup_method(self):
        """Clean up before each test."""
        Provider.objects.all().delete()

    def test_create_provider_with_unique_priority_success(self):
        """Test creating provider with unique priority succeeds."""
        client = APIClient()

        data = {
            "name": ProviderName.MOCK,
            "priority": 1,
            "is_active": True
        }

        response = client.post("/api/v1/exchange/providers/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Provider.objects.filter(priority=1).exists()

    def test_create_provider_with_duplicate_priority_fails(self):
        """Test creating provider with duplicate priority fails with clear error."""
        # Create first provider
        Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        # Try to create second provider with same priority
        client = APIClient()
        data = {
            "name": ProviderName.CURRENCY_BEACON,
            "priority": 1,  # Duplicate!
            "is_active": True
        }

        response = client.post("/api/v1/exchange/providers/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "priority" in response.data
        # Verify error message mentions duplicate/exists
        error_msg = str(response.data["priority"][0]).lower()
        assert "already exists" in error_msg or "already assigned" in error_msg

    def test_update_provider_priority_to_existing_fails(self):
        """Test updating provider priority to an existing one fails."""
        # Create two providers
        provider1 = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )
        provider2 = Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=2,
            is_active=True
        )

        # Try to update provider2's priority to 1 (already used by provider1)
        client = APIClient()
        data = {
            "name": ProviderName.CURRENCY_BEACON,
            "priority": 1,  # Duplicate!
            "is_active": True
        }

        response = client.put(f"/api/v1/exchange/providers/{provider2.id}/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "priority" in response.data
        # Verify duplicate priority is detected
        error_msg = str(response.data["priority"][0]).lower()
        assert "already exists" in error_msg or "already assigned" in error_msg

    def test_update_provider_same_priority_succeeds(self):
        """Test updating provider with same priority (no change) succeeds."""
        provider = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )

        client = APIClient()
        data = {
            "name": ProviderName.MOCK,
            "priority": 1,  # Same priority
            "is_active": False  # Just changing active status
        }

        response = client.put(f"/api/v1/exchange/providers/{provider.id}/", data)

        assert response.status_code == status.HTTP_200_OK
        provider.refresh_from_db()
        assert provider.is_active is False

    def test_swap_priorities_between_providers(self):
        """Test swapping priorities requires updating both providers."""
        provider1 = Provider.objects.create(
            name=ProviderName.MOCK,
            priority=1,
            is_active=True
        )
        provider2 = Provider.objects.create(
            name=ProviderName.CURRENCY_BEACON,
            priority=2,
            is_active=True
        )

        client = APIClient()

        # Step 1: Try to swap directly (should fail)
        response = client.patch(
            f"/api/v1/exchange/providers/{provider1.id}/",
            {"priority": 2}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Step 2: Proper way - move one to temporary, then swap
        # Move provider1 to temp priority
        response = client.patch(
            f"/api/v1/exchange/providers/{provider1.id}/",
            {"priority": 999}
        )
        assert response.status_code == status.HTTP_200_OK

        # Move provider2 to priority 1
        response = client.patch(
            f"/api/v1/exchange/providers/{provider2.id}/",
            {"priority": 1}
        )
        assert response.status_code == status.HTTP_200_OK

        # Move provider1 to priority 2
        response = client.patch(
            f"/api/v1/exchange/providers/{provider1.id}/",
            {"priority": 2}
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify final state
        provider1.refresh_from_db()
        provider2.refresh_from_db()
        assert provider1.priority == 2
        assert provider2.priority == 1

    def test_multiple_providers_all_unique_priorities(self):
        """Test creating multiple providers with all unique priorities."""
        client = APIClient()

        # Create first provider
        response = client.post("/api/v1/exchange/providers/", {
            "name": ProviderName.MOCK,
            "priority": 1,
            "is_active": True
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Create second provider
        response = client.post("/api/v1/exchange/providers/", {
            "name": ProviderName.CURRENCY_BEACON,
            "priority": 2,
            "is_active": True
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Verify both exist
        assert Provider.objects.count() == 2
        assert Provider.objects.filter(priority=1).exists()
        assert Provider.objects.filter(priority=2).exists()
