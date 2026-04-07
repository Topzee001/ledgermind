"""
AI Categorization services using Gemini.

CACHING STRATEGY:
-----------------
The category list (fetched from Transaction Service) is an expensive cross-service
HTTP call that almost never changes between requests.  We cache it per business
for 10 minutes so the AI service doesn't hammer the Transaction Service on every
single categorization.

Key pattern : ai:categories:{business_id}
TTL         : 10 minutes  (CATEGORIES_CACHE_TTL)

Invalidation:
  Call invalidate_categories_cache(business_id) from the Transaction Service
  whenever a category is created, updated, or deleted for that business.
"""
import json
import logging
from django.conf import settings
from django.core.cache import cache
import google.generativeai as genai
from .rules import apply_rule_based_categorization
import requests

logger = logging.getLogger(__name__)

# Cache category lists for 10 minutes — they almost never change mid-session.
CATEGORIES_CACHE_TTL = 60 * 10  # 10 minutes

# Try to initialize Gemini client
gemini_model = None
if getattr(settings, "GEMINI_API_KEY", None):
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _categories_key(business_id: str) -> str:
    """Redis key for a business's category list."""
    return f"ai:categories:{business_id}"


def invalidate_categories_cache(business_id: str) -> None:
    """
    Delete cached categories for a business.
    Call this whenever a category is created / updated / deleted
    so the AI picks up fresh category data on the next request.
    """
    key = _categories_key(business_id)
    cache.delete(key)
    logger.info("Cache INVALIDATED for %s", key)


# ── Service functions ─────────────────────────────────────────────────────────

def fetch_business_categories(business_id: str) -> list:
    """
    Fetch the full list of categories available to a business from the
    Transaction Service, using Redis as a cache to avoid repeated HTTP calls.

    Cache flow:
      CACHE HIT  → return immediately (< 1 ms, no HTTP)
      CACHE MISS → call Transaction Service, store result, return
    """
    key = _categories_key(business_id)

    # ── Try cache first ────────────────────────────────────────────────────
    cached = cache.get(key)
    if cached is not None:
        logger.debug("Cache HIT for %s", key)
        return cached

    # ── Cache miss: call Transaction Service ───────────────────────────────
    logger.debug("Cache MISS for %s — fetching from Transaction Service", key)
    categories = []
    try:
        url = f"{settings.TRANSACTION_SERVICE_URL}/api/v1/categories/?business_id={business_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": settings.SERVICE_SECRET_KEY,
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                categories = data.get("data", [])
    except Exception as exc:
        logger.error("Error fetching categories for business %s: %s", business_id, exc)

    # Store (even an empty list) so we don't retry on every call during an outage
    cache.set(key, categories, timeout=CATEGORIES_CACHE_TTL)
    return categories


def categorize_with_ai(description, amount, trans_type, business_id):
    """
    Categorize a single transaction using Gemini AI, falling back to
    rule-based categorization if AI is unavailable or fails.

    The category list used here comes from the cache (see fetch_business_categories).
    """
    categories = fetch_business_categories(business_id)

    # Only offer the AI categories that match this transaction's type
    allowed_categories = [
        {"id": cat["id"], "name": cat["name"], "description": cat.get("description", "")}
        for cat in categories
        if cat.get("type") in [trans_type, "both"]
    ]

    # Fast path / Fallback: AI not configured
    if not gemini_model or not allowed_categories:
        return _fallback_categorize(description, trans_type, categories, business_id)

    # Gemini Categorization
    try:
        assert gemini_model is not None
        prompt = (
            f"You are a financial accounting assistant categorizing transactions for an SME.\n"
            f"Transaction details:\n"
            f"- Description: {description}\n"
            f"- Amount: {amount}\n"
            f"- Type: {trans_type}\n\n"
            f"Allowed categories (JSON list):\n"
            f"{json.dumps(allowed_categories, indent=2)}\n\n"
            f"Select the most appropriate category from the list above.\n"
            f"Respond with ONLY a valid JSON object containing 'id' and 'name' of the matched category."
        )

        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        if "id" in result and "name" in result:
            return result

    except Exception as exc:
        logger.error("Gemini error: %s", exc)

    # Fallback to rules if AI failed
    return _fallback_categorize(description, trans_type, categories, business_id)


def _create_category_in_transaction_service(name, trans_type, business_id):
    """
    Create a new category in the Transaction Service and return its data.
    Returns the created category dict {'id': ..., 'name': ...} or None on failure.
    """
    try:
        url = f"{settings.TRANSACTION_SERVICE_URL}/api/v1/categories/"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": settings.SERVICE_SECRET_KEY,
        }
        payload = {
            "name": name,
            "type": trans_type,
            "business_id": str(business_id),
            "description": f"Auto-created by AI categorization for '{name}'",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            data = response.json()
            cat = data.get("data", data)
            if cat.get("id"):
                # Invalidate the cache so the new category is picked up next time
                invalidate_categories_cache(business_id)
                logger.info("Auto-created category '%s' (id=%s) for business %s", name, cat["id"], business_id)
                return cat
    except Exception as exc:
        logger.error("Failed to auto-create category '%s' for business %s: %s", name, business_id, exc)
    return None


def _fallback_categorize(description, trans_type, categories, business_id=None):
    """Apply keyword rules and map back to an existing category.
    If no match exists in the DB, auto-create it via the Transaction Service."""
    rule_category_name = apply_rule_based_categorization(description, trans_type)

    for cat in categories:
        if cat["name"].lower() == rule_category_name.lower():
            return {"id": cat["id"], "name": cat["name"], "source": "rules"}

    other_cat = next((c for c in categories if c["name"].lower() == "other"), None)
    if other_cat:
        return {"id": other_cat["id"], "name": other_cat["name"], "source": "rules-default"}

    # No matching category in DB — auto-create it
    if business_id:
        created = _create_category_in_transaction_service(rule_category_name, trans_type, business_id)
        if created:
            return {"id": created["id"], "name": created["name"], "source": "rules-auto-created"}

    return {"id": None, "name": rule_category_name, "source": "rules"}


def categorize_bulk_with_ai(transactions, business_id):
    """
    Categorize a list of transactions in one (or fewer) Gemini prompts.
    The category list is served from the cache just like single categorization.
    """
    categories = fetch_business_categories(business_id)
    if not categories:
        return [{"id": None, "name": "Other", "error": "No categories found"} for _ in transactions]

    # Fallback path — no AI
    if not gemini_model:
        return [_fallback_categorize(t["description"], t.get("type", "expense"), categories, business_id) for t in transactions]

    allowed_categories = [
        {"id": cat["id"], "name": cat["name"], "type": cat.get("type")}
        for cat in categories
    ]

    try:
        prompt = (
            f"You are a financial accounting assistant.\n"
            f"Categorize the following list of transactions for business {business_id}.\n\n"
            f"Allowed categories:\n"
            f"{json.dumps(allowed_categories, indent=2)}\n\n"
            f"Transactions to categorize:\n"
            f"{json.dumps(transactions, indent=2)}\n\n"
            f"Respond with ONLY a JSON list of objects in order, each with 'id' and 'name' of the matched category."
        )

        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )

        results = json.loads(response.text)
        if isinstance(results, list) and len(results) == len(transactions):
            return results
        else:
            logger.warning(
                "Batch AI returned %s entries, expected %s",
                len(results) if isinstance(results, list) else "not a list",
                len(transactions),
            )
    except Exception as exc:
        logger.error("Bulk Gemini error: %s", exc)

    # Fallback for all transactions
    return [_fallback_categorize(t["description"], t.get("type", "expense"), categories, business_id) for t in transactions]
