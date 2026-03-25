"""
Tests for User API endpoints.
TDD: Red → Green → Refactor
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

REGISTER_URL = reverse('users:register')
LOGIN_URL = reverse('users:login')
PROFILE_URL = reverse('users:profile')
TOKEN_REFRESH_URL = reverse('users:token-refresh')


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def create_user():
    """Factory fixture to create users."""
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
    """Return an authenticated API client."""
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_user_success(self, api_client):
        """Test successful user registration."""
        payload = {
            'email': 'new@example.com',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = api_client.post(REGISTER_URL, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['email'] == 'new@example.com'
        assert User.objects.filter(email='new@example.com').exists()

    def test_register_user_short_password(self, api_client):
        """Test registration fails with short password."""
        payload = {
            'email': 'new@example.com',
            'password': 'short',
            'password_confirm': 'short',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_password_mismatch(self, api_client):
        """Test registration fails when passwords don't match."""
        payload = {
            'email': 'new@example.com',
            'password': 'strongpass123',
            'password_confirm': 'differentpass123',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, create_user):
        """Test registration fails with duplicate email."""
        create_user(email='existing@example.com')
        payload = {
            'email': 'existing@example.com',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_email(self, api_client):
        """Test registration fails without email."""
        payload = {
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
        }
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, api_client, create_user):
        """Test successful login returns JWT tokens."""
        create_user(email='login@example.com', password='testpass123')
        payload = {
            'email': 'login@example.com',
            'password': 'testpass123',
        }
        response = api_client.post(LOGIN_URL, payload)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == 'login@example.com'

    def test_login_wrong_password(self, api_client, create_user):
        """Test login fails with wrong password."""
        create_user(email='login@example.com', password='testpass123')
        payload = {
            'email': 'login@example.com',
            'password': 'wrongpassword',
        }
        response = api_client.post(LOGIN_URL, payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login fails for non-existent user."""
        payload = {
            'email': 'nonexistent@example.com',
            'password': 'somepassword',
        }
        response = api_client.post(LOGIN_URL, payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_token_refresh_success(self, api_client, create_user):
        """Test refreshing token returns new access token."""
        create_user(email='refresh@example.com', password='testpass123')
        # First login
        login_response = api_client.post(LOGIN_URL, {
            'email': 'refresh@example.com',
            'password': 'testpass123',
        })
        refresh_token = login_response.data['refresh']

        # Refresh
        response = api_client.post(TOKEN_REFRESH_URL, {
            'refresh': refresh_token,
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_token_refresh_invalid_token(self, api_client):
        """Test refresh fails with invalid token."""
        response = api_client.post(TOKEN_REFRESH_URL, {
            'refresh': 'invalid-token',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    """Test user profile endpoint."""

    def test_get_profile_authenticated(self, authenticated_client):
        """Test getting profile for authenticated user."""
        client, user = authenticated_client
        response = client.get(PROFILE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['email'] == user.email

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile fails for unauthenticated user."""
        response = api_client.get(PROFILE_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, authenticated_client):
        """Test updating user profile."""
        client, user = authenticated_client
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+2348012345678',
        }
        response = client.patch(PROFILE_URL, payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['first_name'] == 'Updated'
        assert response.data['data']['phone_number'] == '+2348012345678'

    def test_update_profile_cannot_change_email(self, authenticated_client):
        """Test that email cannot be changed via profile update."""
        client, user = authenticated_client
        original_email = user.email
        payload = {'email': 'newemail@example.com'}
        response = client.patch(PROFILE_URL, payload)

        # Email should remain unchanged (it's read_only)
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == original_email
