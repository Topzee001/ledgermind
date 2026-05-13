"""
Shared JWT authentication utilities for inter-service communication.
Each microservice uses this to validate JWT tokens from the API Gateway.
"""
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ServiceUser:
    """
    Lightweight user object for inter-service communication.
    Used when validating JWT tokens in services that don't have
    their own User model.
    """
    def __init__(self, user_data):
        self.id = user_data.get('user_id')
        self.email = user_data.get('email', '')
        self.is_authenticated = True

    def __str__(self):
        return f"ServiceUser({self.id})"


class JWTServiceAuthentication(BaseAuthentication):
    """
    Custom JWT authentication for microservices.
    Validates the JWT token and extracts user info without
    needing a local User model.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        print(f"JWT Auth Check on {request.path}: Auth Header = {auth_header}", flush=True)
        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            user = ServiceUser(payload)
            return (user, token)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')


class ServiceToServiceAuthentication(BaseAuthentication):
    """
    Authentication for service-to-service communication.
    Uses a shared service secret key.
    """
    def authenticate(self, request):
        service_key = request.headers.get('X-Service-Key')
        if not service_key:
            return None

        expected_key = getattr(settings, 'SERVICE_SECRET_KEY', None)
        if not expected_key or service_key != expected_key:
            raise AuthenticationFailed('Invalid service key')

        # Return a service user for inter-service calls
        user = ServiceUser({
            'user_id': 'service',
            'email': 'service@internal',
        })
        return (user, service_key)
