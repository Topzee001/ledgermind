"""
Business views.

CACHING STRATEGY:
-----------------
A user's list of businesses is read constantly (on every page load to populate
the business-switcher in the frontend) but rarely changes.  We cache the list
per user.

Key pattern : user:businesses:{user_id}
TTL         : 15 minutes (BUSINESSES_CACHE_TTL)

Individual business detail (GET /{id}/) is NOT cached because it is accessed
less frequently and caching it would require us to track a second key family.

Invalidation:
  - On POST (create new business)   → list is stale, delete user's list key
  - On PUT/PATCH (update business)  → list may show updated name, delete list key
  - On DELETE                       → list is stale, delete user's list key
"""
import logging

from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Business
from .serializers import BusinessListSerializer, BusinessSerializer

logger = logging.getLogger(__name__)

BUSINESSES_CACHE_TTL = 60 * 15  # 15 minutes


def _businesses_list_key(user_id) -> str:
    """Redis key for a user's cached business list."""
    return f"user:businesses:{user_id}"


def _invalidate_businesses_cache(user_id) -> None:
    """
    Delete cached business list for a user.
    Called on any mutation (create / update / delete) so the UI reflects the change.
    """
    key = _businesses_list_key(user_id)
    cache.delete(key)
    logger.info("Business list cache invalidated for user %s", user_id)


class BusinessListCreateView(generics.ListCreateAPIView):
    """
    List all businesses for the authenticated user or create a new one.

    GET  /api/v1/businesses/   → from Redis cache when warm
    POST /api/v1/businesses/   → creates business, then invalidates cache
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BusinessListSerializer
        return BusinessSerializer

    def get_queryset(self):
        return Business.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        Return the business list — from cache if available, from DB otherwise.
        """
        key = _businesses_list_key(request.user.id)

        # ── Try cache ──────────────────────────────────────────────────────
        cached_data = cache.get(key)
        if cached_data is not None:
            logger.debug("Business list cache HIT for user %s", request.user.id)
            return Response({"success": True, "data": cached_data})

        # ── Cache miss → query DB ──────────────────────────────────────────
        logger.debug("Business list cache MISS for user %s — loading from DB", request.user.id)
        queryset = self.get_queryset()
        serializer = BusinessListSerializer(queryset, many=True)
        data = serializer.data

        cache.set(key, data, timeout=BUSINESSES_CACHE_TTL)

        return Response({"success": True, "data": data})

    def create(self, request, *args, **kwargs):
        serializer = BusinessSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        business = serializer.save()

        # ── Invalidate cache ───────────────────────────────────────────────
        # New business added → the cached list is now incomplete.
        _invalidate_businesses_cache(request.user.id)

        return Response(
            {
                "success": True,
                "message": "Business created successfully",
                "data": BusinessSerializer(business).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a business.

    GET    /api/v1/businesses/{id}/
    PUT    /api/v1/businesses/{id}/   → updates DB, invalidates list cache
    PATCH  /api/v1/businesses/{id}/   → updates DB, invalidates list cache
    DELETE /api/v1/businesses/{id}/   → deletes from DB, invalidates list cache
    """
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Business.objects.filter(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # ── Invalidate cache ───────────────────────────────────────────────
        # Business name/details changed → cached list shows old name.
        _invalidate_businesses_cache(request.user.id)

        return Response(
            {
                "success": True,
                "message": "Business updated successfully",
                "data": serializer.data,
            }
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()

        # ── Invalidate cache ───────────────────────────────────────────────
        # Business removed → cached list contains a ghost entry.
        _invalidate_businesses_cache(request.user.id)

        return Response(
            {"success": True, "message": "Business deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )
