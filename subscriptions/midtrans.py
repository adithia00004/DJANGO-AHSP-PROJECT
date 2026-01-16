"""
Midtrans payment gateway integration.

Uses Midtrans Snap API for payment processing.
Documentation: https://docs.midtrans.com/
"""
import hashlib
import json
import logging
import time
from typing import Dict, Optional

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class MidtransError(Exception):
    """Custom exception for Midtrans API errors."""
    pass


class MidtransClient:
    """
    Midtrans Snap API client.
    
    Handles:
    - Creating Snap tokens for payment popup
    - Verifying webhook signatures
    - Checking transaction status
    """
    
    SANDBOX_BASE_URL = "https://app.sandbox.midtrans.com/snap/v1"
    PRODUCTION_BASE_URL = "https://app.midtrans.com/snap/v1"
    
    SANDBOX_API_URL = "https://api.sandbox.midtrans.com/v2"
    PRODUCTION_API_URL = "https://api.midtrans.com/v2"
    
    def __init__(self):
        self.server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '')
        self.client_key = getattr(settings, 'MIDTRANS_CLIENT_KEY', '')
        self.is_production = getattr(settings, 'MIDTRANS_IS_PRODUCTION', False)
        
        if self.is_production:
            self.snap_url = self.PRODUCTION_BASE_URL
            self.api_url = self.PRODUCTION_API_URL
        else:
            self.snap_url = self.SANDBOX_BASE_URL
            self.api_url = self.SANDBOX_API_URL
    
    def _get_auth_header(self) -> Dict:
        """Get Basic Auth header for Midtrans API."""
        import base64
        auth_string = base64.b64encode(f"{self.server_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def create_snap_token(
        self,
        order_id: str,
        amount: int,
        user_email: str,
        user_name: str,
        item_name: str,
        item_id: str = "subscription"
    ) -> Dict:
        """
        Create Snap token for payment popup.
        
        Args:
            order_id: Unique order identifier
            amount: Payment amount in IDR
            user_email: Customer email
            user_name: Customer name
            item_name: Description of purchase
            item_id: Item identifier
        
        Returns:
            Dict with 'token' and 'redirect_url'
        """
        if not self.server_key:
            raise MidtransError("Midtrans server key not configured")
        
        payload = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(amount)
            },
            "customer_details": {
                "email": user_email,
                "first_name": user_name
            },
            "item_details": [
                {
                    "id": item_id,
                    "price": int(amount),
                    "quantity": 1,
                    "name": item_name
                }
            ],
            "callbacks": {
                "finish": f"{settings.SITE_URL}/subscriptions/payment/finish/"
            }
        }
        
        try:
            response = requests.post(
                f"{self.snap_url}/transactions",
                headers=self._get_auth_header(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "token": data.get("token"),
                "redirect_url": data.get("redirect_url")
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Midtrans API error: {e}")
            raise MidtransError(f"Payment gateway error: {str(e)}")
    
    def verify_signature(
        self,
        order_id: str,
        status_code: str,
        gross_amount: str,
        signature: str
    ) -> bool:
        """
        Verify webhook signature from Midtrans.
        
        Signature = SHA512(order_id + status_code + gross_amount + server_key)
        """
        raw_string = f"{order_id}{status_code}{gross_amount}{self.server_key}"
        expected_signature = hashlib.sha512(raw_string.encode()).hexdigest()
        return signature == expected_signature
    
    def get_transaction_status(self, order_id: str) -> Optional[Dict]:
        """
        Get transaction status from Midtrans API.
        
        Returns transaction details or None if not found.
        """
        try:
            response = requests.get(
                f"{self.api_url}/{order_id}/status",
                headers=self._get_auth_header(),
                timeout=30
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting transaction status: {e}")
            return None


# Singleton instance
midtrans_client = MidtransClient()
