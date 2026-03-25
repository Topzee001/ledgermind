"""
Shared utility functions for all microservices.
"""
import uuid
import requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status


def generate_uuid():
    """Generate a new UUID4."""
    return uuid.uuid4()


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """Standard success response format."""
    response_data = {
        'success': True,
        'message': message,
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)


def error_response(message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Standard error response format."""
    response_data = {
        'success': False,
        'message': message,
    }
    if errors is not None:
        response_data['errors'] = errors
    return Response(response_data, status=status_code)


def call_service(service_url, method='GET', data=None, headers=None, timeout=10):
    """
    Make an HTTP call to another microservice.
    
    Args:
        service_url: Full URL of the target service endpoint
        method: HTTP method (GET, POST, PUT, DELETE)
        data: Request body (dict)
        headers: Additional headers
        timeout: Request timeout in seconds
    
    Returns:
        Response data as dict or None on failure
    """
    default_headers = {
        'Content-Type': 'application/json',
        'X-Service-Key': getattr(settings, 'SERVICE_SECRET_KEY', ''),
    }
    if headers:
        default_headers.update(headers)

    try:
        response = requests.request(
            method=method,
            url=service_url,
            json=data,
            headers=default_headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {'error': str(e), 'success': False}


# Service URLs - configured via environment variables
SERVICE_URLS = {
    'user_service': 'http://localhost:8001',
    'transaction_service': 'http://localhost:8002',
    'ai_service': 'http://localhost:8003',
    'analytics_service': 'http://localhost:8004',
    'payment_service': 'http://localhost:8005',
}


def get_service_url(service_name, path=''):
    """Get the full URL for a service endpoint."""
    base_url = SERVICE_URLS.get(service_name, '')
    return f"{base_url}{path}"
