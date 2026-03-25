"""
Custom exception handlers and exceptions for all microservices.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


def custom_exception_handler(exc, context):
    """Custom exception handler that ensures consistent error responses."""
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': _extract_message(response.data),
                'details': response.data if isinstance(response.data, dict) else None,
            }
        }

    return response


def _extract_message(data):
    """Extract a readable error message from DRF error data."""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        # Get the first field error
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            elif isinstance(value, str):
                return f"{key}: {value}"
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable.'
    default_code = 'service_unavailable'


class ExternalAPIError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'External API request failed.'
    default_code = 'external_api_error'


class InvalidDataError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'The provided data is invalid.'
    default_code = 'invalid_data'
