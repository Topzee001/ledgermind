"""
Tests for Transaction API endpoints.
TDD: Red → Green → Refactor

Key changes reflected:
  - Redis cache invalidation on create/update/delete.
  - Cache key pattern: dashboard:transactions:{business_id}
  - AI categorization via Gemini (mocked in tests).
"""
import uuid
import pytest
import io
import datetime
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from transactions.models import Transaction
from categories.models import Category
from unittest.mock import patch, MagicMock

LIST_CREATE_URL = reverse('transactions:list-create')
UPLOAD_CSV_URL = reverse('transactions:upload-csv')

def detail_url(pk):
    return reverse('transactions:detail', args=[pk])


@pytest.fixture
def auth_client():
    client = APIClient()
    client.credentials(HTTP_X_SERVICE_KEY=settings.SERVICE_SECRET_KEY)
    return client

@pytest.fixture
def business_id():
    return str(uuid.uuid4())


@pytest.mark.django_db
class TestTransactionEndpoints:

    def test_list_transactions(self, auth_client, business_id):
        """Test listing transactions with and without business_id filter."""
        cat = Category.objects.create(name='Food', type='expense')
        Transaction.objects.create(
            business_id=business_id, category=cat, type='expense',
            amount=100.00, date=datetime.date.today(), description='Lunch'
        )

        # Another business
        Transaction.objects.create(
            business_id=str(uuid.uuid4()), category=cat, type='expense',
            amount=50.00, date=datetime.date.today(), description='Coffee'
        )

        # Without filter
        res1 = auth_client.get(LIST_CREATE_URL)
        assert len(res1.data['data']) == 2

        # With business_id
        res2 = auth_client.get(f"{LIST_CREATE_URL}?business_id={business_id}")
        assert len(res2.data['data']) == 1

    @patch('transactions.views.categorize_transaction_via_ai')
    def test_create_transaction_with_ai(self, mock_ai, auth_client, business_id):
        """Test transaction fallback to AI categorization."""
        cat = Category.objects.create(name='Technology', type='expense')

        # Mocking the AI service returning a category dictionary format expected
        mock_ai.return_value = {
            'id': str(cat.id),
            'name': cat.name,
            'type': cat.type
        }

        payload = {
            'business_id': business_id,
            'amount': 2500,
            'type': 'expense',
            'date': '2026-03-24',
            'description': 'Server Hosting Fees',
            'source': 'manual'
        }

        res = auth_client.post(LIST_CREATE_URL, payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED

        txn = Transaction.objects.get(id=res.data['data']['id'])
        assert txn is not None

    def test_upload_csv(self, auth_client, business_id):
        """Test CSV bulk upload creates transactions."""
        csv_content = b"date,amount,type,description\n2026-03-01,150,expense,Dinner\n2026-03-02,500,income,Sales"
        csv_file = io.BytesIO(csv_content)
        csv_file.name = "export.csv"

        res = auth_client.post(UPLOAD_CSV_URL, {'business_id': business_id, 'file': csv_file}, format='multipart')

        assert res.status_code == status.HTTP_201_CREATED
        assert Transaction.objects.filter(business_id=business_id).count() == 2


@pytest.mark.django_db
class TestTransactionCacheInvalidation:
    """
    TDD tests for cache invalidation on transaction writes.

    The Transaction Service invalidates the Analytics Service's
    cached data (key: dashboard:transactions:{business_id}) whenever
    a transaction is created, updated, or deleted.
    """

    @patch('transactions.views.categorize_transaction_via_ai')
    def test_create_invalidates_cache(self, mock_ai, auth_client, business_id):
        """
        RED:   Before adding _invalidate_transaction_cache() to create → fails.
        GREEN: After adding cache.delete() in create() → passes.

        Creating a transaction should invalidate the dashboard cache
        so analytics reflects the new data immediately.
        """
        cat = Category.objects.create(name='Food', type='expense')
        mock_ai.return_value = {'id': str(cat.id), 'name': 'Food', 'type': 'expense'}

        payload = {
            'business_id': business_id,
            'amount': 100,
            'type': 'expense',
            'date': '2026-03-24',
            'description': 'Lunch',
            'source': 'manual'
        }

        with patch('transactions.views.cache.delete') as mock_cache_delete:
            res = auth_client.post(LIST_CREATE_URL, payload, format='json')
            assert res.status_code == status.HTTP_201_CREATED

            # Verify cache was invalidated for this business
            mock_cache_delete.assert_called_with(f"dashboard:transactions:{business_id}")

    def test_delete_invalidates_cache(self, auth_client, business_id):
        """
        Deleting a transaction should also invalidate the dashboard cache.
        """
        cat = Category.objects.create(name='Food', type='expense')
        txn = Transaction.objects.create(
            business_id=business_id, category=cat, type='expense',
            amount=100, date=datetime.date.today(), description='Lunch'
        )

        with patch('transactions.views.cache.delete') as mock_cache_delete:
            res = auth_client.delete(detail_url(txn.id))
            assert res.status_code == status.HTTP_204_NO_CONTENT

            mock_cache_delete.assert_called_with(f"dashboard:transactions:{business_id}")

    def test_update_invalidates_cache(self, auth_client, business_id):
        """
        Updating a transaction should invalidate the dashboard cache.
        """
        cat = Category.objects.create(name='Food', type='expense')
        txn = Transaction.objects.create(
            business_id=business_id, category=cat, type='expense',
            amount=100, date=datetime.date.today(), description='Lunch'
        )

        with patch('transactions.views.cache.delete') as mock_cache_delete:
            res = auth_client.patch(detail_url(txn.id), {'amount': 200, 'type': 'expense'}, format='json')
            assert res.status_code == status.HTTP_200_OK

            mock_cache_delete.assert_called_with(f"dashboard:transactions:{business_id}")
