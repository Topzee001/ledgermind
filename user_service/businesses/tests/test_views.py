"""
Tests for Business API endpoints.
TDD: Red → Green → Refactor

Key changes reflected:
  - Business list caching in Redis (key: user:businesses:{user_id}).
  - Cache invalidation on create/update/delete.
"""
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from businesses.models import Business

User = get_user_model()

BUSINESS_LIST_URL = reverse('businesses:list-create')


def business_detail_url(business_id):
    """Return business detail URL."""
    return reverse('businesses:detail', args=[business_id])


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_user():
    def _create_user(**kwargs):
        defaults = {
            'email': 'testuser@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    return _create_user


@pytest.fixture
def authenticated_client(api_client, create_user):
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestBusinessCreate:
    """Test creating businesses."""

    def test_create_business_success(self, authenticated_client):
        """Test creating a business successfully."""
        client, user = authenticated_client
        payload = {
            'name': 'My SME',
            'industry': 'retail',
            'description': 'A small retail business',
        }
        response = client.post(BUSINESS_LIST_URL, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['name'] == 'My SME'
        assert Business.objects.filter(owner=user).count() == 1

    def test_create_business_unauthenticated(self, api_client):
        """Test creating a business fails without auth."""
        payload = {'name': 'My SME', 'industry': 'retail'}
        response = api_client.post(BUSINESS_LIST_URL, payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_business_missing_name(self, authenticated_client):
        """Test creating a business fails without name."""
        client, _ = authenticated_client
        payload = {'industry': 'retail'}
        response = client.post(BUSINESS_LIST_URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_multiple_businesses(self, authenticated_client):
        """Test a user can create multiple businesses."""
        client, user = authenticated_client
        for i in range(3):
            payload = {'name': f'Business {i}', 'industry': 'retail'}
            client.post(BUSINESS_LIST_URL, payload)

        assert Business.objects.filter(owner=user).count() == 3


@pytest.mark.django_db
class TestBusinessList:
    """Test listing businesses."""

    def test_list_own_businesses(self, authenticated_client):
        """Test listing only the authenticated user's businesses."""
        client, user = authenticated_client
        Business.objects.create(owner=user, name='Business 1', industry='retail')
        Business.objects.create(owner=user, name='Business 2', industry='technology')

        # Create another user's business (should not appear)
        other_user = User.objects.create_user(
            email='other@example.com', password='pass123'
        )
        Business.objects.create(owner=other_user, name='Other Business')

        response = client.get(BUSINESS_LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2


@pytest.mark.django_db
class TestBusinessDetail:
    """Test business detail, update, and delete."""

    def test_get_business_detail(self, authenticated_client):
        """Test retrieving a specific business."""
        client, user = authenticated_client
        business = Business.objects.create(
            owner=user, name='My Business', industry='retail'
        )
        response = client.get(business_detail_url(business.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['name'] == 'My Business'

    def test_update_business(self, authenticated_client):
        """Test updating a business."""
        client, user = authenticated_client
        business = Business.objects.create(
            owner=user, name='Original', industry='retail'
        )
        response = client.patch(
            business_detail_url(business.id),
            {'name': 'Updated Name'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['name'] == 'Updated Name'

    def test_delete_business(self, authenticated_client):
        """Test deleting a business."""
        client, user = authenticated_client
        business = Business.objects.create(
            owner=user, name='To Delete', industry='retail'
        )
        response = client.delete(business_detail_url(business.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Business.objects.filter(id=business.id).exists()

    def test_cannot_access_other_users_business(self, api_client, create_user):
        """Test that user cannot access another user's business."""
        user1 = create_user(email='user1@example.com')
        user2 = create_user(email='user2@example.com')

        business = Business.objects.create(
            owner=user1, name='Private Business', industry='retail'
        )

        api_client.force_authenticate(user=user2)
        response = api_client.get(business_detail_url(business.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBusinessListCaching:
    """
    TDD tests for Redis caching of the business list.

    The cache key pattern is: user:businesses:{user_id}
    - GET /businesses/  → cache.get(key) → if miss: query DB, cache.set(key)
    - POST/PUT/DELETE   → cache.delete(key) to invalidate
    """

    def test_list_cache_hit_and_miss(self, authenticated_client):
        """
        RED:   Before implementing caching → cache is never consulted.
        GREEN: After adding cache logic in list() → test passes.
        """
        client, user = authenticated_client
        cache_key = f"user:businesses:{user.id}"

        Business.objects.create(owner=user, name='Cached Biz', industry='technology')

        with patch('businesses.views.cache.get') as mock_cache_get, \
             patch('businesses.views.cache.set') as mock_cache_set:

            # Simulate cache MISS
            mock_cache_get.return_value = None

            response = client.get(BUSINESS_LIST_URL)
            assert response.status_code == status.HTTP_200_OK

            mock_cache_get.assert_called_with(cache_key)
            assert mock_cache_set.called is True

            # Simulate cache HIT
            mock_cache_get.return_value = [{'id': '1', 'name': 'Cached Biz'}]
            mock_cache_set.reset_mock()

            response2 = client.get(BUSINESS_LIST_URL)
            assert response2.status_code == status.HTTP_200_OK
            assert mock_cache_set.called is False

    def test_create_invalidates_cache(self, authenticated_client):
        """Creating a business invalidates the list cache."""
        client, user = authenticated_client
        cache_key = f"user:businesses:{user.id}"

        with patch('businesses.views.cache.delete') as mock_cache_delete:
            payload = {'name': 'New Biz', 'industry': 'technology'}
            response = client.post(BUSINESS_LIST_URL, payload)
            assert response.status_code == status.HTTP_201_CREATED

            mock_cache_delete.assert_called_with(cache_key)

    def test_update_invalidates_cache(self, authenticated_client):
        """Updating a business invalidates the list cache."""
        client, user = authenticated_client
        business = Business.objects.create(owner=user, name='Old', industry='retail')
        cache_key = f"user:businesses:{user.id}"

        with patch('businesses.views.cache.delete') as mock_cache_delete:
            response = client.patch(business_detail_url(business.id), {'name': 'New'})
            assert response.status_code == status.HTTP_200_OK

            mock_cache_delete.assert_called_with(cache_key)

    def test_delete_invalidates_cache(self, authenticated_client):
        """Deleting a business invalidates the list cache."""
        client, user = authenticated_client
        business = Business.objects.create(owner=user, name='Bye', industry='retail')
        cache_key = f"user:businesses:{user.id}"

        with patch('businesses.views.cache.delete') as mock_cache_delete:
            response = client.delete(business_detail_url(business.id))
            assert response.status_code == status.HTTP_204_NO_CONTENT

            mock_cache_delete.assert_called_with(cache_key)
