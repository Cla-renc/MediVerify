import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.inventory.models import Pharmacy


@pytest.mark.django_db
def test_professional_registration_creates_inactive_pharmacy_account(api_client):
    response = api_client.post('/api/v1/auth/register/', {
        'username': 'new_pharmacist',
        'email': 'new-pharmacist@example.test',
        'password': 'private-password-123',
        'role': 'PHARMACIST',
        'organization_name': 'New Chemist',
        'license_number': 'PHARMACY-NEW-001',
        'address': 'Nairobi',
        'county': 'Nairobi',
    }, format='json')

    assert response.status_code == 201
    user = get_user_model().objects.get(username='new_pharmacist')
    assert user.is_active is False
    assert user.is_staff is False
    assert user.role == 'PHARMACIST'
    assert Pharmacy.objects.get(user=user).license_number == 'PHARMACY-NEW-001'
    assert response.data['pending_approval'] is True


@pytest.mark.django_db
def test_public_registration_is_active_but_regulator_role_is_not_self_assignable(api_client):
    public_response = api_client.post('/api/v1/auth/register/', {
        'username': 'new_customer',
        'email': 'customer@example.test',
        'password': 'private-password-123',
        'role': 'PUBLIC',
    }, format='json')
    rejected_response = api_client.post('/api/v1/auth/register/', {
        'username': 'fake_regulator',
        'email': 'fake-regulator@example.test',
        'password': 'private-password-123',
        'role': 'REGULATOR',
    }, format='json')

    assert public_response.status_code == 201
    assert get_user_model().objects.get(username='new_customer').is_active is True
    assert rejected_response.status_code == 400
    assert not get_user_model().objects.filter(username='fake_regulator').exists()


@pytest.mark.django_db
def test_public_statistics_are_aggregate_and_update_after_scan(api_client, sample_unit_code):
    before = api_client.get('/api/v1/reports/stats/')
    assert before.status_code == 200
    assert 'scans_today' in before.data
    assert 'ip_address' not in before.data

    verification = api_client.post('/api/v1/verify/', {
        'code': sample_unit_code.secure_code,
        'channel': 'WEB_MANUAL',
    }, format='json')
    after = api_client.get('/api/v1/reports/stats/')

    assert verification.status_code == 200
    assert after.data['total_scans'] == before.data['total_scans'] + 1
    assert after.data['scans_today'] == before.data['scans_today'] + 1


@pytest.mark.django_db
def test_verification_result_receipt_downloads_pdf(api_client, sample_unit_code):
    verification = api_client.post('/api/v1/verify/', {
        'code': sample_unit_code.secure_code,
        'channel': 'WEB_MANUAL',
    }, format='json')
    scan_id = verification.data['verification_details']['scan_id']

    receipt = api_client.get(f'/api/v1/verify/receipt/{scan_id}/')

    assert receipt.status_code == 200
    assert receipt['Content-Type'] == 'application/pdf'
    assert receipt.content.startswith(b'%PDF')


@pytest.mark.django_db
def test_regulator_websocket_authenticates_and_receives_clone_alert(regulator_user):
    from mediverify.asgi import application
    from channels.testing import WebsocketCommunicator

    access_token = str(RefreshToken.for_user(regulator_user).access_token)

    async def exercise_socket():
        communicator = WebsocketCommunicator(
            application,
            '/ws/clone-alerts/',
            subprotocols=['mediverify', access_token],
        )
        connected, protocol = await communicator.connect()
        assert connected is True
        assert protocol == 'mediverify'
        ready = await communicator.receive_json_from()
        assert ready == {'type': 'connected'}
        await get_channel_layer().group_send('clone_alerts', {
            'type': 'clone.alert',
            'payload': {'type': 'clone_alert', 'alert_id': 'alert-1'},
        })
        notification = await communicator.receive_json_from()
        assert notification == {'type': 'clone_alert', 'alert_id': 'alert-1'}
        await communicator.disconnect()

    async_to_sync(exercise_socket)()


@pytest.mark.django_db
def test_regulator_websocket_rejects_missing_credentials():
    from mediverify.asgi import application
    from channels.testing import WebsocketCommunicator

    async def exercise_socket():
        communicator = WebsocketCommunicator(application, '/ws/clone-alerts/')
        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == 4401

    async_to_sync(exercise_socket)()
