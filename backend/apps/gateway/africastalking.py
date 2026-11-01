import logging
import hmac

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AfricaTalkingError(RuntimeError):
    pass


def send_sms(phone_number, message):
    if not settings.AFRICASTALKING_ENABLED:
        raise AfricaTalkingError("Africa's Talking SMS delivery is disabled.")

    username = settings.AFRICASTALKING_USERNAME
    api_key = settings.AFRICASTALKING_API_KEY
    if not username or not api_key or api_key == 'sandbox_api_key_placeholder':
        raise AfricaTalkingError("Africa's Talking username and API key must be configured.")

    payload = {
        'username': username,
        'to': phone_number,
        'message': message,
    }
    if settings.AFRICASTALKING_SENDER_ID:
        payload['from'] = settings.AFRICASTALKING_SENDER_ID

    try:
        response = requests.post(
            f'{settings.AFRICASTALKING_BASE_URL.rstrip("/")}/version1/messaging',
            data=payload,
            headers={
                'apiKey': api_key,
                'Accept': 'application/json',
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.exception("Africa's Talking SMS request failed.")
        raise AfricaTalkingError("Could not deliver the SMS through Africa's Talking.") from exc

    recipients = (
        data.get('SMSMessageData', {}).get('Recipients', [])
        if isinstance(data, dict) and isinstance(data.get('SMSMessageData'), dict)
        else []
    )
    if not recipients or any(
        not isinstance(recipient, dict)
        or (
            recipient.get('status') != 'Success'
            and str(recipient.get('statusCode')) not in {'100', '101', '102'}
        )
        for recipient in recipients
    ):
        logger.error("Africa's Talking returned an unsuccessful SMS delivery response.")
        raise AfricaTalkingError("Africa's Talking did not accept the SMS for delivery.")

    return data


def callback_is_authorized(request):
    if not settings.AFRICASTALKING_ENABLED:
        return True

    expected_token = settings.AFRICASTALKING_CALLBACK_TOKEN
    if not expected_token:
        logger.error("Africa's Talking is enabled but its callback token is not configured.")
        return False

    supplied_token = request.GET.get('token', '')
    return hmac.compare_digest(supplied_token, expected_token)
