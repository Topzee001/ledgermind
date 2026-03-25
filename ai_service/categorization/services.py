"""
AI Categorization services using OpenAI.
"""
import json
import logging
from django.conf import settings
from openai import OpenAI
from .rules import apply_rule_based_categorization
import requests

logger = logging.getLogger(__name__)

# Try to initialize OpenAI client
client = None
if getattr(settings, 'OPENAI_API_KEY', None):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)


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
    if not client or not allowed_categories:
        return _fallback_categorize(description, trans_type, categories)
        
    # OpenAI Categorization
    try:
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
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        if 'id' in result and 'name' in result:
            return result
        
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        
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
