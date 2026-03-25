"""Interswitch Payment Services."""
import base64
import requests
import time
from django.conf import settings

class InterswitchService:
    @staticmethod
    def get_access_token():
        """
        Retrieves OAuth 2.0 access token from Interswitch passport.
        """
        auth_string = f"{settings.ISW_CLIENT_ID}:{settings.ISW_SECRET_KEY}"
        b64_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        url = f"{settings.ISW_BASE_URL}/passport/oauth/token"
        
        try:
            # We bypass real HTTP calls in tests normally.
            # But here is the real implementation for production.
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                return response.json().get('access_token')
            else:
                print(f"Interswitch Token Error: {response.text}")
        except Exception as e:
            print(f"Token Network Error: {e}")
            
        return None

    @staticmethod
    def initiate_payment(amount, reference, callback_url):
        """
        Initiates a quickteller business transaction. 
        Returns a payment link or redirect URL.
        """
        token = InterswitchService.get_access_token()
        if not token:
            return None
            
        url = f"{settings.ISW_BASE_URL}/api/v3/purchases"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Payload according to standard ISW checkout initialization
        # The schema can vary slightly depending on API product used.
        # This acts as a standard representation for the Hackathon.
        payload = {
            "amount": str(int(amount * 100)), # Amount in kobo
            "transactionRef": reference,
            "currency": "NGN",
            "siteRedirectURL": callback_url
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code in [200, 201]:
                return response.json()
        except Exception as e:
            print(f"ISW Initiate Payment Error: {e}")
            
        return None
