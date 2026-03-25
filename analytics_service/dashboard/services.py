"""Dashboard services for fetching transaction data."""
import requests
from django.conf import settings

def fetch_business_transactions(business_id):
    """
    Fetch all transactions for a business from Transaction Service.
    Authenticates using service-to-service key.
    """
    url = f"{settings.TRANSACTION_SERVICE_URL}/api/v1/transactions/?business_id={business_id}"
    headers = {
        "X-Service-Key": settings.SERVICE_SECRET_KEY,
        "Accept": "application/json"
    }
    try:
        # Fetching all transactions for analytics (ideally would be filtered by date here too)
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Handle paginated or non-paginated requests from Transaction service
            if isinstance(data.get('data'), list):
                return data['data']
            elif 'results' in data.get('data', {}):
                return data['data']['results']
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        
    return []
