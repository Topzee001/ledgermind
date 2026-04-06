"""
Views for the User Service.

CACHING STRATEGY:
-----------------
User profile data is read far more often than it is written.  Every time the
frontend renders the header/navbar it likely hits the profile endpoint.  We
cache it per user.

Key pattern : user:profile:{user_id}
TTL         : 15 minutes (USER_PROFILE_CACHE_TTL)

Invalidation:
  When the user calls PUT/PATCH on /api/v1/users/profile/, we delete the
  cached key so the very next GET returns the fresh data.
"""
import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Cache profile data for 15 minutes.
# The profile (name, email, etc.) changes rarely, so a longer TTL is fine.
USER_PROFILE_CACHE_TTL = 60 * 15  # 15 minutes


def _profile_cache_key(user_id) -> str:
    """Redis key for a user's cached profile."""
    return f"user:profile:{user_id}"


def _invalidate_user_profile_cache(user_id) -> None:
    """
    Delete the cached user profile.
    Called after any profile update so the next GET returns fresh data.
    """
    key = _profile_cache_key(user_id)
    cache.delete(key)
    logger.info("Profile cache invalidated for user %s", user_id)


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user account.

    POST /api/v1/users/register/
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "success": True,
                "message": "User registered successfully",
                "data": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserLoginView(TokenObtainPairView):
    """
    Login and receive JWT tokens.

    POST /api/v1/users/login/
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.

    POST /api/v1/users/token/refresh/
    """
    pass


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update the authenticated user's profile.

    GET   /api/v1/users/profile/   → served from Redis cache when warm
    PUT   /api/v1/users/profile/   → updates DB, then invalidates cache
    PATCH /api/v1/users/profile/   → updates DB, then invalidates cache
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """
        Return the profile — from cache if available, from DB otherwise.

        Cache flow:
          1. Check Redis for `user:profile:{user_id}`
          2. CACHE HIT  → return immediately
          3. CACHE MISS → query DB, serialise, store in Redis, return
        """
        key = _profile_cache_key(request.user.id)

        # ── Try cache ──────────────────────────────────────────────────────
        cached_data = cache.get(key)
        if cached_data is not None:
            logger.debug("Profile cache HIT for user %s", request.user.id)
            return Response({"success": True, "data": cached_data})

        # ── Cache miss → query DB ──────────────────────────────────────────
        logger.debug("Profile cache MISS for user %s — loading from DB", request.user.id)
        serializer = self.get_serializer(request.user)
        profile_data = serializer.data

        cache.set(key, profile_data, timeout=USER_PROFILE_CACHE_TTL)

        return Response({"success": True, "data": profile_data})

    def update(self, request, *args, **kwargs):
        """
        Update the profile, then invalidate the cache so the
        next GET reflects the new data.
        """
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(request.user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ── Invalidate cache ───────────────────────────────────────────────
        # Profile was updated → stale data must not be served on next GET.
        _invalidate_user_profile_cache(request.user.id)

        return Response(
            {
                "success": True,
                "message": "Profile updated successfully",
                "data": serializer.data,
            }
        )


class HealthCheckView(APIView):
    """Health check endpoint with database connectivity test."""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection

        db_status = "connected"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as exc:
            db_status = f"error: {exc}"

        return Response(
            {
                "status": "healthy" if db_status == "connected" else "degraded",
                "service": "user-service",
                "database": db_status,
            }
        )
