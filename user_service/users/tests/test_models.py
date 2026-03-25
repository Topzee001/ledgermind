"""
Tests for User models.
TDD: Red → Green → Refactor
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test cases for the custom User model."""

    def test_create_user_with_email(self):
        """Test creating a user with email is successful."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
        )
        assert user.email == 'test@example.com'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        assert user.check_password('testpass123')
        assert user.is_active is True
        assert user.is_staff is False

    def test_new_user_email_normalized(self):
        """Test email is normalized for new users."""
        emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
        ]
        for email, expected in emails:
            user = User.objects.create_user(email=email, password='test123')
            assert user.email == expected

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises ValueError."""
        with pytest.raises(ValueError):
            User.objects.create_user(email='', password='test123')

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
        )
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_user_full_name(self):
        """Test the full_name property."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            first_name='John',
            last_name='Doe',
        )
        assert user.full_name == 'John Doe'

    def test_user_string_representation(self):
        """Test the string representation of a user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123',
        )
        assert str(user) == 'test@example.com'

    def test_user_uuid_primary_key(self):
        """Test that user has UUID primary key."""
        user = User.objects.create_user(
            email='test@example.com',
            password='test123',
        )
        assert user.id is not None
        assert len(str(user.id)) == 36  # UUID format
