import requests
import base64
from django.conf import settings
from decouple import config
import logging

logger = logging.getLogger(__name__)


class BEEMSMSService:
    """Service for sending SMS using BEEM Africa API"""

    def __init__(self):
        self.api_key = config('BEEM_API_KEY', default='')
        self.secret_key = config('BEEM_SECRET_KEY', default='')
        self.sender_id = config('BEEM_SENDER_ID', default='caluuplus')
        self.admin_phone = config('BEEM_ADMIN_PHONE', default='0614021404')
        self.api_url = "https://apisms.beem.africa/public/v1/send"

        # Log configuration for debugging
        logger.info(f"BEEM SMS Service initialized with admin_phone: {self.admin_phone}")
        logger.info(f"API Key configured: {bool(self.api_key)}")
        logger.info(f"Secret Key configured: {bool(self.secret_key)}")

    def _get_auth_header(self):
        """Generate Basic Auth header using API key and secret key"""
        credentials = f"{self.api_key}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    def send_sms(self, recipient, message):
        """
        Send SMS to a recipient

        Args:
            recipient (str): Phone number (format: 255XXXXXXXXX or 06XXXXXXXXX)
            message (str): SMS message content

        Returns:
            dict: Response from BEEM API
        """
        try:
            logger.info(f"Attempting to send SMS to {recipient}")
            logger.info(f"Message content: {message[:100]}...")  # Log first 100 chars

            # Normalize phone number format
            if recipient.startswith('0'):
                recipient = '255' + recipient[1:]

            logger.info(f"Normalized phone number: {recipient}")

            headers = {
                'Authorization': self._get_auth_header(),
                'Content-Type': 'application/json'
            }

            payload = {
                'source_addr': self.sender_id,
                'schedule_time': '',
                'encoding': '0',
                'message': message,
                'recipients': [recipient]
            }

            logger.info(f"Sending request to BEEM API: {self.api_url}")
            logger.info(f"Payload: {payload}")

            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)

            logger.info(f"BEEM API response status: {response.status_code}")
            logger.info(f"BEEM API response body: {response.text}")

            if response.status_code == 200:
                logger.info(f"✅ SMS sent successfully to {recipient}")
                return {'success': True, 'data': response.json()}
            else:
                logger.error(f"❌ SMS failed to {recipient}: {response.text}")
                return {'success': False, 'error': response.text}

        except Exception as e:
            logger.error(f"❌ SMS sending error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_admin_notification(self, message):
        """
        Send SMS notification to admin phone number

        Args:
            message (str): SMS message content

        Returns:
            dict: Response from BEEM API
        """
        logger.info(f"Sending admin notification to {self.admin_phone}")
        return self.send_sms(self.admin_phone, message)


# Singleton instance
sms_service = BEEMSMSService()


def send_registration_sms(user_email, user_name):
    """Send SMS notification when a new user registers"""
    message = f"New user registered: {user_name} ({user_email})"
    return sms_service.send_admin_notification(message)


def send_zero_token_sms(user_email, user_name):
    """Send SMS notification when user with zero tokens tries to export"""
    message = f"Zero token export attempt: {user_name} ({user_email})"
    return sms_service.send_admin_notification(message)


def send_transaction_sms(user_email, user_name, amount, transaction_type):
    """Send SMS notification when a billing transaction is submitted"""
    message = f"Transaction submitted: {user_name} ({user_email}) - {transaction_type}: {amount}"
    return sms_service.send_admin_notification(message)
