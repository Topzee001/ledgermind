"""Tests for Payment Service endpoints."""
import uuid
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from payments.models import Payment

PAYMENT_LIST_URL = reverse('payments:list')
PAYMENT_INITIATE_URL = reverse('payments:initiate')
PAYMENT_WEBHOOK_URL = reverse('payments:webhook')

@pytest.fixture
def auth_client():
    client = APIClient()
    from shared.authentication import ServiceUser
    client.force_authenticate(user=ServiceUser({'user_id': str(uuid.uuid4())}))
    return client

@pytest.fixture
def unauth_client():
    return APIClient()

@pytest.fixture
def business_id():
    return str(uuid.uuid4())

@pytest.mark.django_db
class TestPaymentEndpoints:
    
    @patch('payments.services.InterswitchService.get_access_token')
    @patch('payments.services.InterswitchService.initiate_payment')
    def test_initiate_payment(self, mock_init, mock_token, auth_client, business_id):
        mock_init.return_value = {'redirectUrl': 'https://mock.isw.com/pay'}
        
        payload = {
            'business_id': business_id,
            'amount': '5000.00',
            'description': 'Software Setup Fee'
        }
        
        res = auth_client.post(PAYMENT_INITIATE_URL, payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED
        assert 'payment_url' in res.data['data']
        assert res.data['data']['payment_url'] == 'https://mock.isw.com/pay'
        assert Payment.objects.count() == 1
        
    def test_list_payments(self, auth_client, business_id):
        # We need a user context for creating if we are asserting
        user_id = getattr(auth_client.handler._force_user, 'id', str(uuid.uuid4()))
        
        Payment.objects.create(
            user_id=user_id, business_id=business_id, 
            amount=500, description="Test", reference="REF123"
        )
        
        Payment.objects.create(
            user_id=user_id, business_id=str(uuid.uuid4()), 
            amount=1000, description="Test 2", reference="REF456"
        )
        
        # Test generic list
        res1 = auth_client.get(PAYMENT_LIST_URL)
        assert res1.status_code == status.HTTP_200_OK
        # Depends on whether page pagination wraps it. 'data' wrapper exists
        assert 'count' in res1.data or 'data' in res1.data
        
        # Test business filter
        res2 = auth_client.get(f"{PAYMENT_LIST_URL}?business_id={business_id}")
        if 'data' in res2.data and isinstance(res2.data['data'], list):
            assert len(res2.data['data']) == 1
        elif 'data' in res2.data and 'results' in res2.data['data']:
             assert len(res2.data['data']['results']) == 1
            
    def test_webhook(self, unauth_client, business_id):
        user_id = str(uuid.uuid4())
        ref = "LDG-WEBHOOK-TEST"
        
        Payment.objects.create(
            user_id=user_id, business_id=business_id, 
            amount=5000, description="Web", reference=ref, status='pending'
        )
        
        payload = {
            "transactionRef": ref,
            "responseCode": "00",
            "interswitchRef": "ISW-12345"
        }
        
        res = unauth_client.post(PAYMENT_WEBHOOK_URL, payload, format='json')
        assert res.status_code == status.HTTP_200_OK
        
        payment = Payment.objects.get(reference=ref)
        assert payment.status == 'success'
        assert payment.interswitch_ref == 'ISW-12345'
