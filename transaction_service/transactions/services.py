"""
Services for Transaction operations (e.g. calling AI service).
"""
import requests
from django.conf import settings

def categorize_transaction_via_ai(description, amount, type, business_id):
    """
    Calls the AI service to categorize the transaction.
    Returns the category dictionary if successful, or None.
    """
    try:
        url = f"{settings.AI_SERVICE_URL}/api/v1/categorize/"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": settings.SERVICE_SECRET_KEY
        }
        payload = {
            "description": description,
            "amount": float(amount),
            "type": type,
            "business_id": str(business_id)
        }
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {}).get('category')
    except Exception as e:
        # Silently fail and return None for AI categorization errors
        print(f"AI Categorization Error: {e}")
    return None


def categorize_bulk_via_ai(transactions_data, business_id):
    """
    Calls AI service to categorize multiple transactions at once.
    :param transactions_data: List of dicts with description, amount, type
    :param business_id: Business UUID
    :returns: List of category dicts or empty list
    """
    try:
        url = f"{settings.AI_SERVICE_URL}/api/v1/categorize/bulk/"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": settings.SERVICE_SECRET_KEY
        }
        payload = {
            "business_id": str(business_id),
            "transactions": transactions_data
        }
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {}).get('categories', [])
    except Exception as e:
        print(f"AI Bulk Categorization Error: {e}")
    return []
