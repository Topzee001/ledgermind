"""
Tests for AI Categorization Service API endpoints.
TDD: Red → Green → Refactor

Key changes reflected here:
  - AI engine was migrated from OpenAI → Gemini.
  - The module-level variable is now `gemini_model` not `client`.
  - Redis caching was added for category lists (cache key: ai:categories:{business_id}).
"""
import uuid
import pytest
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

CATEGORIZE_URL = reverse('categorization:categorize')

@pytest.fixture
def auth_client():
    client = APIClient()
    client.credentials(HTTP_X_SERVICE_KEY=settings.SERVICE_SECRET_KEY)
    return client

@pytest.fixture
def business_id():
    return str(uuid.uuid4())

class TestCategorizeTransaction:

    @patch('categorization.services.fetch_business_categories')
    def test_categorize_fallback_rules(self, mock_fetch, auth_client, business_id):
        """
        When gemini_model is None (AI not configured), the service falls back
        to rule-based keyword matching.
        'shoprite' in description → matches 'Groceries' category.
        """
        cat_id = str(uuid.uuid4())
        mock_fetch.return_value = [
            {'id': cat_id, 'name': 'Groceries', 'type': 'expense'},
            {'id': str(uuid.uuid4()), 'name': 'Other', 'type': 'expense'}
        ]

        payload = {
            'description': 'Bought food at Shoprite',
            'amount': 5000,
            'type': 'expense',
            'business_id': business_id
        }

        # Patch gemini_model to None so AI is disabled → falls back to rules
        with patch('categorization.services.gemini_model', None):
            res = auth_client.post(CATEGORIZE_URL, payload, format='json')

            assert res.status_code == status.HTTP_200_OK
            assert res.data['success'] is True
            assert res.data['data']['category']['id'] == cat_id
            assert res.data['data']['category']['name'] == 'Groceries'

    @patch('categorization.services.fetch_business_categories')
    def test_categorize_unmatched_rules_fallback_to_other(self, mock_fetch, auth_client, business_id):
        """
        When no keyword rule matches and AI is disabled,
        the system falls back to the 'Other' category.
        """
        cat_id = str(uuid.uuid4())
        other_id = str(uuid.uuid4())
        mock_fetch.return_value = [
            {'id': cat_id, 'name': 'Rent', 'type': 'expense'},
            {'id': other_id, 'name': 'Other', 'type': 'expense'}
        ]

        payload = {
            'description': 'Random random random',
            'amount': 100,
            'type': 'expense',
            'business_id': business_id
        }

        with patch('categorization.services.gemini_model', None):
            res = auth_client.post(CATEGORIZE_URL, payload, format='json')

            assert res.status_code == status.HTTP_200_OK
            assert res.data['success'] is True
            assert res.data['data']['category']['id'] == other_id
            assert res.data['data']['category']['name'] == 'Other'

    def test_categorize_missing_parameters(self, auth_client):
        """POST without required fields returns 400."""
        payload = {
            'description': 'Bought food at Shoprite',
        }
        res = auth_client.post(CATEGORIZE_URL, payload, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthorized_access(self):
        """Requests without service key are rejected with 403."""
        client = APIClient()
        res = client.post(CATEGORIZE_URL, {'description': 'Food', 'business_id': str(uuid.uuid4())}, format='json')
        assert res.status_code == status.HTTP_403_FORBIDDEN


class TestCategoryCaching:
    """
    TDD tests for the Redis caching layer on category fetches.

    The cache key pattern is: ai:categories:{business_id}
    - fetch_business_categories() checks cache first, then HTTP on miss.
    - invalidate_categories_cache() deletes the key.
    """

    @patch('categorization.services.requests.get')
    def test_cache_miss_fetches_from_service(self, mock_get, business_id):
        """
        RED:   No caching implemented → cache.get/set never called.
        GREEN: Add cache logic to fetch_business_categories() → passes.

        On a cache MISS the function should call the Transaction Service
        via HTTP and then store the result in Redis.
        """
        mock_get.return_value = type('Response', (), {
            'status_code': 200,
            'json': lambda self: {'success': True, 'data': [
                {'id': str(uuid.uuid4()), 'name': 'Food', 'type': 'expense'}
            ]}
        })()

        with patch('categorization.services.cache.get', return_value=None) as mock_cache_get, \
             patch('categorization.services.cache.set') as mock_cache_set:

            from categorization.services import fetch_business_categories
            result = fetch_business_categories(business_id)

            mock_cache_get.assert_called_once_with(f"ai:categories:{business_id}")
            assert mock_cache_set.called is True
            assert len(result) == 1

    def test_cache_hit_skips_http(self, business_id):
        """
        When data IS in the cache, we return it directly without HTTP.
        """
        cached_cats = [{'id': 'abc', 'name': 'Cached', 'type': 'expense'}]

        with patch('categorization.services.cache.get', return_value=cached_cats) as mock_cache_get, \
             patch('categorization.services.requests.get') as mock_http:

            from categorization.services import fetch_business_categories
            result = fetch_business_categories(business_id)

            mock_cache_get.assert_called_once()
            mock_http.assert_not_called()
            assert result == cached_cats

    def test_cache_invalidation(self, business_id):
        """
        invalidate_categories_cache() must delete the correct Redis key.
        """
        with patch('categorization.services.cache.delete') as mock_delete:
            from categorization.services import invalidate_categories_cache
            invalidate_categories_cache(business_id)

            mock_delete.assert_called_once_with(f"ai:categories:{business_id}")
