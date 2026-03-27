"""
AI Categorization services using Gemini.
"""
import json
import logging
from django.conf import settings
import google.generativeai as genai
from .rules import apply_rule_based_categorization
import requests

logger = logging.getLogger(__name__)

# Try to initialize Gemini client
gemini_model = None
if getattr(settings, 'GEMINI_API_KEY', None):
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')


def fetch_business_categories(business_id):
    """
    Fetch both default and custom categories available for this business
    from the Transaction Service.
    """
    try:
        url = f"{settings.TRANSACTION_SERVICE_URL}/api/v1/categories/?business_id={business_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": settings.SERVICE_SECRET_KEY
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
    except Exception as e:
        logger.error(f"Error fetching categories from transaction service: {e}")
    return []


def categorize_with_ai(description, amount, trans_type, business_id):
    """
    Categorize a transaction based on its description, amount, and type.
    Uses OpenAI by default, falls back to rules if OpenAI is not configured or fails.
    """
    categories = fetch_business_categories(business_id)
    
    # We only want to categorize into an existing category ID if possible.
    # We tell AI the valid categories.
    allowed_categories = [
        {"id": cat['id'], "name": cat['name'], "description": cat.get('description', '')} 
        for cat in categories if cat.get('type') in [trans_type, 'both']
    ]
    
    # Fast path/Fallback: AI not configured
    if not gemini_model or not allowed_categories:
        return _fallback_categorize(description, trans_type, categories)
        
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
        if 'id' in result and 'name' in result:
            return result
        
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        
    # Fallback to rules if AI failed
    return _fallback_categorize(description, trans_type, categories)


def _fallback_categorize(description, trans_type, categories):
    """Helper to apply rules and map back to existing categories or return 'Other' category."""
    rule_category_name = apply_rule_based_categorization(description, trans_type)
    
    # Find matching category by name in the fetched list
    for cat in categories:
        if cat['name'].lower() == rule_category_name.lower():
            return {"id": cat['id'], "name": cat['name'], "source": "rules"}
            
    # Default fallback
    other_cat = next((c for c in categories if c['name'].lower() == 'other'), None)
    if other_cat:
        return {"id": other_cat['id'], "name": other_cat['name'], "source": "rules-default"}
        
    # Worst case, just return the name chosen by rules
    return {"id": None, "name": rule_category_name, "source": "rules"}


def categorize_bulk_with_ai(transactions, business_id):
    """
    Categorize a list of transactions in one or fewer Gemini prompts.
    :param transactions: List of dicts with {'description', 'amount', 'type'}
    :param business_id: Business UUID
    :returns: List of dicts with categorization results
    """
    categories = fetch_business_categories(business_id)
    if not categories:
        return [{"id": None, "name": "Other", "error": "No categories found"} for _ in transactions]
        
    # Categorize using rules for speed or fallback
    if not gemini_model:
        return [_fallback_categorize(t['description'], t.get('type', 'expense'), categories) for t in transactions]
        
    # Group transactions for AI (Gemini can handle many at once)
    allowed_categories = [
        {"id": cat['id'], "name": cat['name'], "type": cat.get('type')} 
        for cat in categories
    ]
    
    try:
        # Prompt for batch categorization
        prompt = (
            f"You are a financial accounting assistant.\n"
            f"Categorize the following list of transactions for business {business_id}.\n\n"
            f"Allowed categories:\n"
            f"{json.dumps(allowed_categories, indent=2)}\n\n"
            f"Transactions to categorize:\n"
            f"{json.dumps(transactions, indent=2)}\n\n"
            f"Respond with a ONLY a JSON list of objects in order, each with 'id' and 'name' of the matched category."
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
            logger.warning(f"Batch AI returned {len(results) if isinstance(results, list) else 'not a list'} entries, expected {len(transactions)}")
    except Exception as e:
        logger.error(f"Bulk Gemini error: {e}")
        
    # Fallback for all
    return [_fallback_categorize(t['description'], t.get('type', 'expense'), categories) for t in transactions]
