"""
Shared permissions for all microservices.
"""
from rest_framework.permissions import BasePermission


class IsServiceRequest(BasePermission):
    """
    Permission check for inter-service communication.
    """
    def has_permission(self, request, view):
        return request.headers.get('X-Service-Key') is not None


class IsAuthenticatedUser(BasePermission):
    """
    Permission check for authenticated users via JWT.
    """
    def has_permission(self, request, view):
        return (
            request.user is not None and
            hasattr(request.user, 'is_authenticated') and
            request.user.is_authenticated
        )
