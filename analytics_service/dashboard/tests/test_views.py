"""
Tests for Analytics Service API endpoints.
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
    
    @patch('dashboard.services.fetch_business_transactions')
    def test_dashboard_data(self, mock_fetch, auth_client, business_id):
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

class TestForecasting:
    
    @patch('forecasting.views.fetch_business_transactions')
    def test_cashflow_forecast(self, mock_fetch, auth_client, business_id):
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
