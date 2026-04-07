"""
Tests for Analytics Service API endpoints.
TDD: Red → Green → Refactor

Key changes reflected:
  - Dashboard transactions are now cached in Redis (key: dashboard:transactions:{business_id}).
  - fetch_business_transactions() has cache-hit/miss logic.
  - invalidate_business_transactions_cache() deletes the cache key.
"""
import uuid
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

@pytest.fixture
def auth_client():
    client = APIClient()
    # Mocking standard user authentication via JWT payload user
    client.credentials(HTTP_AUTHORIZATION='Bearer dummy')
    from shared.authentication import ServiceUser
    client.force_authenticate(user=ServiceUser({'user_id': str(uuid.uuid4())}))
    return client

@pytest.fixture
def business_id():
    return str(uuid.uuid4())

class TestDashboardAnalytics:

    @patch('dashboard.views.fetch_business_transactions')
    def test_dashboard_data(self, mock_fetch, auth_client, business_id):
        """Test dashboard correctly aggregates income, expense, and trends."""
        mock_fetch.return_value = [
            {'amount': 500, 'type': 'income', 'date': '2026-03-01', 'category_detail': {'name': 'Sales'}},
            {'amount': 100, 'type': 'expense', 'date': '2026-03-02', 'category_detail': {'name': 'Food'}},
        ]

        url = reverse('dashboard:dashboard-data', args=[business_id])
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data['data']['overview']['net_profit'] == 400
        assert res.data['data']['expense_by_category']['Food'] == 100
        assert '2026-03' in res.data['data']['monthly_trends']

    @patch('dashboard.views.fetch_business_transactions')
    def test_dashboard_empty_transactions(self, mock_fetch, auth_client, business_id):
        """Test dashboard handles zero transactions gracefully."""
        mock_fetch.return_value = []

        url = reverse('dashboard:dashboard-data', args=[business_id])
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data['data']['overview']['net_profit'] == 0
        assert res.data['data']['expense_by_category'] == {}

class TestForecasting:

    @patch('forecasting.views.fetch_business_transactions')
    def test_cashflow_forecast(self, mock_fetch, auth_client, business_id):
        """Test forecasting generates 3-month projections based on moving average."""
        mock_fetch.return_value = [
            {'amount': 1000, 'type': 'income', 'date': '2026-01-01'},
            {'amount': 500, 'type': 'expense', 'date': '2026-01-15'},
            {'amount': 1200, 'type': 'income', 'date': '2026-02-01'},
            {'amount': 600, 'type': 'expense', 'date': '2026-02-15'},
        ]

        url = reverse('forecasting:forecast-cashflow', args=[business_id])
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['data']) == 3  # Next 3 months
        # Avg income: (1000+1200)/2 = 1100
        assert res.data['data'][0]['projected_income'] == 1100

class TestCreditScore:

    @patch('credit_score.views.fetch_business_transactions')
    def test_credit_score_calculation(self, mock_fetch, auth_client, business_id):
        """Test credit score algorithm with profitable business data."""
        mock_fetch.return_value = [
            {'amount': 5000, 'type': 'income', 'date': '2026-01-01'},
            {'amount': 500, 'type': 'expense', 'date': '2026-01-15'},
            {'amount': 5000, 'type': 'income', 'date': '2026-02-01'},
            {'amount': 500, 'type': 'expense', 'date': '2026-02-15'},
        ]

        url = reverse('credit_score:score', args=[business_id])
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert 'score' in res.data['data']
        assert res.data['data']['metrics']['months_active'] == 2
        assert res.data['data']['metrics']['is_profitable_overall'] is True

    @patch('credit_score.views.fetch_business_transactions')
    def test_credit_score_no_data(self, mock_fetch, auth_client, business_id):
        """Test credit score returns 0 when there are no transactions."""
        mock_fetch.return_value = []

        url = reverse('credit_score:score', args=[business_id])
        res = auth_client.get(url)

        assert res.status_code == status.HTTP_200_OK
        assert res.data['data']['score'] == 0


class TestDashboardCaching:
    """
    TDD tests for the Redis caching layer on dashboard transaction fetches.

    The cache key pattern is: dashboard:transactions:{business_id}
    - fetch_business_transactions() checks cache → HTTP on miss → stores result.
    - invalidate_business_transactions_cache() deletes the key.
    """

    @patch('dashboard.services.requests.get')
    def test_cache_miss_fetches_from_transaction_service(self, mock_get, business_id):
        """
        RED:   Before caching → cache.get/set are never called.
        GREEN: After adding cache logic → this test passes.

        On a MISS, the function should call Transaction Service via HTTP
        and then store the response data in Redis.
        """
        mock_get.return_value = type('Response', (), {
            'status_code': 200,
            'json': lambda self: {'data': [
                {'amount': 500, 'type': 'income', 'date': '2026-03-01'}
            ]}
        })()

        with patch('dashboard.services.cache.get', return_value=None) as mock_cache_get, \
             patch('dashboard.services.cache.set') as mock_cache_set:

            from dashboard.services import fetch_business_transactions
            result = fetch_business_transactions(business_id)

            mock_cache_get.assert_called_once_with(f"dashboard:transactions:{business_id}")
            assert mock_cache_set.called is True
            assert len(result) == 1

    def test_cache_hit_skips_http(self, business_id):
        """When data IS in the cache, we return it directly without HTTP."""
        cached_txns = [{'amount': 100, 'type': 'expense'}]

        with patch('dashboard.services.cache.get', return_value=cached_txns) as mock_get, \
             patch('dashboard.services.requests.get') as mock_http:

            from dashboard.services import fetch_business_transactions
            result = fetch_business_transactions(business_id)

            mock_get.assert_called_once()
            mock_http.assert_not_called()
            assert result == cached_txns

    def test_cache_invalidation(self, business_id):
        """invalidate_business_transactions_cache() deletes the correct Redis key."""
        with patch('dashboard.services.cache.delete') as mock_delete:
            from dashboard.services import invalidate_business_transactions_cache
            invalidate_business_transactions_cache(business_id)

            mock_delete.assert_called_once_with(f"dashboard:transactions:{business_id}")
