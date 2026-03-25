"""
Tests for AI Categorization Service API endpoints.
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
        
        # Test fallback triggering word matching "shoprite" -> "Groceries"
        with patch('categorization.services.client', None):  # Mock OpenAI client is None
            res = auth_client.post(CATEGORIZE_URL, payload, format='json')
            
            assert res.status_code == status.HTTP_200_OK
            assert res.data['success'] is True
            assert res.data['data']['category']['id'] == cat_id
            assert res.data['data']['category']['name'] == 'Groceries'

    @patch('categorization.services.fetch_business_categories')
    def test_categorize_unmatched_rules_fallback_to_other(self, mock_fetch, auth_client, business_id):
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
        
        with patch('categorization.services.client', None):
            res = auth_client.post(CATEGORIZE_URL, payload, format='json')
            
            assert res.status_code == status.HTTP_200_OK
            assert res.data['success'] is True
            assert res.data['data']['category']['id'] == other_id
            assert res.data['data']['category']['name'] == 'Other'

    def test_categorize_missing_parameters(self, auth_client):
        payload = {
            'description': 'Bought food at Shoprite',
        }
        res = auth_client.post(CATEGORIZE_URL, payload, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthorized_access(self):
        client = APIClient()
        res = client.post(CATEGORIZE_URL, {'description': 'Food', 'business_id': str(uuid.uuid4())}, format='json')
        assert res.status_code == status.HTTP_403_FORBIDDEN
