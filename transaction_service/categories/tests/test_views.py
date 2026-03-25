import uuid
import pytest
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from categories.models import Category

URL = reverse('categories:list-create')


@pytest.fixture
def auth_client():
    client = APIClient()
    client.credentials(HTTP_X_SERVICE_KEY=settings.SERVICE_SECRET_KEY)
    return client


@pytest.mark.django_db
class TestCategoryListCreate:
    
    def test_list_default_categories(self, auth_client):
        """Test default categories are returned without business_id"""
        Category.objects.create(name='Food', type='expense', is_default=True)
        Category.objects.create(name='Salary', type='income', is_default=True)
        
        response = auth_client.get(URL)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2
        
    def test_list_categories_with_business(self, auth_client):
        """Test listing categories includes both default and custom for business"""
        b_id = str(uuid.uuid4())
        
        Category.objects.create(name='Food', type='expense', is_default=True)
        Category.objects.create(name='Custom Software', type='expense', business_id=b_id)
        
        # Test getting without business id
        res1 = auth_client.get(URL)
        assert len(res1.data['data']) == 1
        
        # Test getting with business id
        res2 = auth_client.get(f"{URL}?business_id={b_id}")
        assert len(res2.data['data']) == 2

    def test_create_category(self, auth_client):
        """Test creating custom category requires business_id"""
        payload = {
            'name': 'New Custom',
            'type': 'expense',
            'description': 'Something new'
            # Missing business_id
        }
        res = auth_client.post(URL, payload, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        
        # Now with business_id
        payload['business_id'] = str(uuid.uuid4())
        res2 = auth_client.post(URL, payload, format='json')
        assert res2.status_code == status.HTTP_201_CREATED
        assert res2.data['data']['name'] == 'New Custom'
        assert not res2.data['data']['is_default']
