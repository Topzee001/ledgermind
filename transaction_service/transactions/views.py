"""
Transaction views.

CACHE INVALIDATION STRATEGY:
-----------------------------
Two downstream services read transaction data from this service:
  - Analytics Service  →  caches `dashboard:transactions:{business_id}`
  - AI Service         →  caches `ai:categories:{business_id}`

Whenever a transaction is written (created, updated, deleted), the cached
data for that business becomes stale.  We therefore call cache.delete() on
the relevant Redis key right after every write.

The key pattern is the same string used in analytics_service/dashboard/services.py:
    "dashboard:transactions:{business_id}"

We also invalidate the analytics service's cached dashboard data because
the analytics service holds its own copy of transaction data in Redis.

NOTE: We only invalidate the TRANSACTION cache here.  The CATEGORY cache
(`ai:categories:*`) is only invalidated when a category changes — that is
handled inside the Categories views (see categories/views.py, if it exists)
or wherever categories are mutated.
"""
import csv
import io
import logging

from django.core.cache import cache
from django.db import transaction
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from categories.models import Category
from .models import Transaction
from .serializers import TransactionSerializer, TransactionUploadSerializer
from .services import categorize_bulk_via_ai, categorize_transaction_via_ai

logger = logging.getLogger(__name__)

# ── Cache key helpers ─────────────────────────────────────────────────────────
# These mirror the keys defined in the Analytics and AI services so we
# can invalidate from here.

def _dashboard_cache_key(business_id) -> str:
    """The key the Analytics Service uses to cache transactions for a business."""
    return f"dashboard:transactions:{business_id}"


def _invalidate_transaction_cache(business_id) -> None:
    """
    Delete the cached transaction list for a business.

    Called after any write (create / update / delete) so the Analytics Service
    returns fresh data on the very next dashboard request.
    """
    key = _dashboard_cache_key(business_id)
    deleted = cache.delete(key)
    logger.info(
        "Transaction cache invalidated for business %s (key=%s, deleted=%s)",
        business_id, key, deleted,
    )


# ── Views ─────────────────────────────────────────────────────────────────────

class TransactionListCreateView(generics.ListCreateAPIView):
    """
    List all transactions for a business or create a new one.

    GET  /api/v1/transactions/?business_id=uuid
    POST /api/v1/transactions/

    On POST (create): cache for this business is invalidated so the next
    analytics/dashboard request fetches fresh data.
    """
    serializer_class = TransactionSerializer

    def get_queryset(self):
        business_id = self.request.query_params.get("business_id")
        queryset = Transaction.objects.all()
        if business_id:
            queryset = queryset.filter(business_id=business_id)

        type_filter = self.request.query_params.get("type")
        if type_filter in ["income", "expense"]:
            queryset = queryset.filter(type=type_filter)

        return queryset

    def create(self, request, *args, **kwargs):
        business_id = request.data.get("business_id")
        if not business_id:
            return Response(
                {"success": False, "message": "business_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        category_id = serializer.validated_data.get("category")
        description = serializer.validated_data.get("description", "")
        amount = serializer.validated_data.get("amount")
        trans_type = serializer.validated_data.get("type")

        ai_categorized = False

        if not category_id and description:
            ai_category_data = categorize_transaction_via_ai(
                description, amount, trans_type, business_id
            )
            if ai_category_data and ai_category_data.get("id"):
                try:
                    cat = Category.objects.get(id=ai_category_data["id"])
                    serializer.validated_data["category"] = cat
                    ai_categorized = True
                except Category.DoesNotExist:
                    pass

        transaction_instance = serializer.save(ai_categorized=ai_categorized)

        # ── Invalidate cache ───────────────────────────────────────────────
        # A new transaction was added → analytics data is now stale.
        _invalidate_transaction_cache(business_id)

        return Response(
            {
                "success": True,
                "message": "Transaction created successfully",
                "data": TransactionSerializer(transaction_instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.get_paginated_response(serializer.data)
            res.data["success"] = True
            return res

        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a transaction.

    GET    /api/v1/transactions/{id}/
    PUT    /api/v1/transactions/{id}/
    PATCH  /api/v1/transactions/{id}/
    DELETE /api/v1/transactions/{id}/

    On PUT / PATCH / DELETE: cache for this business is invalidated.
    """
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # If the user manually changes the category, mark it as non-AI categorized
        if (
            "category" in serializer.validated_data
            and serializer.validated_data["category"] != instance.category
        ):
            serializer.validated_data["ai_categorized"] = False

        serializer.save()

        # ── Invalidate cache ───────────────────────────────────────────────
        # Transaction data changed → analytics totals are now stale.
        _invalidate_transaction_cache(instance.business_id)

        return Response(
            {
                "success": True,
                "message": "Transaction updated successfully",
                "data": serializer.data,
            }
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        business_id = instance.business_id  # capture before deletion
        instance.delete()

        # ── Invalidate cache ───────────────────────────────────────────────
        # A transaction was removed → analytics totals are now stale.
        _invalidate_transaction_cache(business_id)

        return Response(
            {"success": True, "message": "Transaction deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


class TransactionCSVUploadView(generics.GenericAPIView):
    """
    Upload a CSV for bulk transaction import.

    POST /api/v1/transactions/upload/

    After all rows are inserted: cache for this business is invalidated once,
    so analytics reflects the newly imported batch on the next request.
    """
    serializer_class = TransactionUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business_id = serializer.validated_data["business_id"]
        file = serializer.validated_data["file"]

        if not file.name.endswith(".csv"):
            return Response(
                {"success": False, "message": "Only CSV files are allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decoded_file = file.read().decode("utf-8")
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        raw_rows = []
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                type_val = row.get("type", "expense").lower() or "expense"
                amount_val = float(row.get("amount", 0))
                date_val = row.get("date")
                desc_val = row.get("description", "")

                if not date_val:
                    errors.append(f"Row {idx}: Missing date")
                    continue

                raw_rows.append(
                    {
                        "type": type_val,
                        "amount": amount_val,
                        "date": date_val,
                        "description": desc_val,
                        "idx": idx,
                    }
                )
            except Exception as exc:
                errors.append(f"Row {idx}: Data error - {exc}")

        if not raw_rows:
            return Response(
                {
                    "success": False,
                    "message": "No valid transactions found in CSV",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ai_data = [
            {"description": r["description"], "amount": r["amount"], "type": r["type"]}
            for r in raw_rows
        ]
        categorized_results = categorize_bulk_via_ai(ai_data, business_id)

        transactions_to_create = []
        for i, row in enumerate(raw_rows):
            cat_id = None
            ai_flag = False
            if i < len(categorized_results):
                cat_id = categorized_results[i].get("id")
                ai_flag = bool(cat_id)

            transactions_to_create.append(
                Transaction(
                    business_id=business_id,
                    type=row["type"],
                    amount=row["amount"],
                    date=row["date"],
                    description=row["description"],
                    category_id=cat_id,
                    ai_categorized=ai_flag,
                    source="csv",
                )
            )

        if transactions_to_create:
            with transaction.atomic():
                Transaction.objects.bulk_create(transactions_to_create)

        # ── Invalidate cache once for the whole batch ──────────────────────
        # Many transactions were added → analytics totals are now stale.
        _invalidate_transaction_cache(business_id)

        return Response(
            {
                "success": True,
                "message": (
                    f"Imported and AI-categorized {len(transactions_to_create)} transactions. "
                    f"{len(errors)} errors."
                ),
                "errors": errors,
            },
            status=status.HTTP_201_CREATED,
        )
