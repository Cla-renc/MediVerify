from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from apps.gateway.africastalking import AfricaTalkingError, send_sms


@override_settings(
    AFRICASTALKING_ENABLED=True,
    AFRICASTALKING_USERNAME='mv-live',
    AFRICASTALKING_API_KEY='test-api-key',
    AFRICASTALKING_BASE_URL='https://api.africastalking.com',
    AFRICASTALKING_SENDER_ID='MediVerify',
)
def test_send_sms_uses_africas_talking_messaging_api():
    response = Mock()
    response.json.return_value = {
        'SMSMessageData': {
            'Recipients': [{'status': 'Success', 'statusCode': 101}],
        },
    }

    with patch('apps.gateway.africastalking.requests.post', return_value=response) as post:
        send_sms('+254700000000', 'MediVerify test')

    post.assert_called_once_with(
        'https://api.africastalking.com/version1/messaging',
        data={
            'username': 'mv-live',
            'to': '+254700000000',
            'message': 'MediVerify test',
            'from': 'MediVerify',
        },
        headers={'apiKey': 'test-api-key', 'Accept': 'application/json'},
        timeout=15,
    )


@override_settings(
    AFRICASTALKING_ENABLED=True,
    AFRICASTALKING_USERNAME='mv-live',
    AFRICASTALKING_API_KEY='test-api-key',
    AFRICASTALKING_BASE_URL='https://api.africastalking.com',
    AFRICASTALKING_SENDER_ID='',
)
def test_send_sms_raises_on_provider_rejection():
    response = Mock()
    response.json.return_value = {
        'SMSMessageData': {
            'Recipients': [{'status': 'Failed', 'statusCode': 400}],
        },
    }

    with patch('apps.gateway.africastalking.requests.post', return_value=response):
        with pytest.raises(AfricaTalkingError, match='did not accept'):
            send_sms('+254700000000', 'MediVerify test')


@pytest.mark.django_db
@override_settings(
    AFRICASTALKING_ENABLED=True,
    AFRICASTALKING_USERNAME='mv-live',
    AFRICASTALKING_API_KEY='test-api-key',
    AFRICASTALKING_BASE_URL='https://api.africastalking.com',
    AFRICASTALKING_SENDER_ID='',
    AFRICASTALKING_CALLBACK_TOKEN='callback-secret',
)
def test_live_sms_callback_requires_token_and_sends_reply(api_client):
    unauthorized = api_client.post(
        '/api/v1/gateway/sms/',
        {'from': '+254700000000', 'text': 'MV-UNKNOWN-CODE'},
        format='json',
    )
    assert unauthorized.status_code == 403

    with patch('apps.gateway.views.send_sms') as send:
        response = api_client.post(
            '/api/v1/gateway/sms/?token=callback-secret',
            {'from': '+254700000000', 'text': 'MV-UNKNOWN-CODE'},
            format='json',
        )

    assert response.status_code == 200
    assert response.data['status'] == 'SUCCESS'
    send.assert_called_once()
    assert send.call_args.args[0] == '+254700000000'
    assert 'INVALID CODE' in send.call_args.args[1]
