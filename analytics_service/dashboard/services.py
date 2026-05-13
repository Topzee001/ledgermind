"""
Dashboard services for fetching transaction data.

CACHING STRATEGY:
-----------------
We cache the raw transaction list for each business with a 5 min TTL (DASHBOARD_CACHE_TTL).
The key pattern `dashboard:transactions:{business_id}` means we can find and
delete the key precisely whenever a transaction is created, updated, or deleted
in the Transaction Service — that's the cache invalidation step.

Why cache here?
  - The Analytics, Forecasting, and CreditScore views all call this same
    fetch_business_transactions() function independently.  Without caching,
    every single API hit from the frontend fires an outbound HTTP request
    to the Transaction Service AND triggers a database query there.
  - With caching, the FIRST request pays the cost; every subsequent request
    within the TTL window reads from Redis in < 1 ms.
"""
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# How long (seconds) to keep transaction data in the cache.
# 5 minutes is a safe default: analytics data can tolerate being slightly stale,
# but fresh enough that users see recent transactions soon after creating them.
DASHBOARD_CACHE_TTL = 60 * 5  # 5 minutes


def _cache_key(business_id: str) -> str:
    """Return the Redis key for a business's cached transactions."""
    return f"dashboard:transactions:{business_id}"


def fetch_business_transactions(business_id: str, force_refresh: bool = False) -> list:
    """
    Fetch transactions with an optional force_refresh to bypass cache.
    """
    key = _cache_key(business_id)

    # Only check cache if we aren't forcing a refresh
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            logger.debug("Cache HIT for %s", key)
            return cached

    logger.debug("Fetching fresh data from Transaction Service (Refresh=%s)", force_refresh)
    # We add limit=1000 to bypass the default 20-row pagination for analytics calculations
    url = f"{settings.TRANSACTION_SERVICE_URL}/api/v1/transactions/?business_id={business_id}&limit=1000"
    headers = {
        "X-Service-Key": settings.SERVICE_SECRET_KEY,
        "Accept": "application/json",
    }
    transactions = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Handle both paginated { data: { results: [...] } } and flat { data: [...] }
            if isinstance(data.get("data"), list):
                transactions = data["data"]
            elif "results" in data.get("data", {}):
                transactions = data["data"]["results"]
    except Exception as exc:
        logger.error("Error fetching transactions for business %s: %s", business_id, exc)

    # ── Step 3: Store result in Redis ──────────────────────────────────────
    # We store even an empty list so repeated failures don't spam the service.
    cache.set(key, transactions, timeout=DASHBOARD_CACHE_TTL)

    return transactions


def invalidate_business_transactions_cache(business_id: str) -> None:
    """
    Delete the cached transaction list for a specific business.

    Call this whenever a transaction is written (created / updated / deleted)
    so the next analytics request re-fetches fresh data from the DB.
    """
    key = _cache_key(business_id)
    cache.delete(key)
    logger.info("Cache INVALIDATED for %s", key)
