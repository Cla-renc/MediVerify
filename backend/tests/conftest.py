"""
pytest conftest.py — Django test fixtures shared across all test modules.
"""
import pytest
from django.conf import settings


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def regulator_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        username='test_regulator',
        email='regulator@test.co.ke',
        password='regulator123',
        role='REGULATOR'
    )


@pytest.fixture
def manufacturer_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='test_manufacturer',
        email='mfg@test.co.ke',
        password='mfg123',
        role='MANUFACTURER',
        organization_name='Test Pharma Kenya'
    )


@pytest.fixture
def pharmacist_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='test_pharmacist',
        email='pharma@test.co.ke',
        password='pharma123',
        role='PHARMACIST',
        organization_name='Test Pharmacy Nairobi'
    )


@pytest.fixture
def auth_client_regulator(api_client, regulator_user):
    """APIClient authenticated as a regulator."""
    api_client.force_authenticate(user=regulator_user)
    return api_client


@pytest.fixture
def auth_client_manufacturer(api_client, manufacturer_user):
    """APIClient authenticated as a manufacturer."""
    api_client.force_authenticate(user=manufacturer_user)
    return api_client


@pytest.fixture
def auth_client_pharmacist(api_client, pharmacist_user):
    """APIClient authenticated as a pharmacist."""
    api_client.force_authenticate(user=pharmacist_user)
    return api_client


@pytest.fixture
def system_settings(db):
    """Create default system settings."""
    from apps.reports.models import SystemSettings
    return SystemSettings.get_settings()


@pytest.fixture
def sample_manufacturer(db):
    from apps.products.models import Manufacturer
    return Manufacturer.objects.create(
        name='TestPharma Kenya Ltd',
        license_number='TEST-PPB-CONFTEST-001',
        country='Kenya',
        contact_email='test@testpharma.co.ke',
        is_verified=True
    )


@pytest.fixture
def sample_product(db, sample_manufacturer):
    from apps.products.models import Product
    return Product.objects.create(
        manufacturer=sample_manufacturer,
        brand_name='ConfTest 500',
        generic_name='Testamine',
        dosage_form='Tablet',
        strength='500mg',
        usage_instructions_en='Take once daily.',
        usage_instructions_sw='Kunywa mara moja kwa siku.',
        side_effects_en='None known.',
        side_effects_sw='Hakuna inayojulikana.',
        key_warnings_en='Keep away from children.',
        key_warnings_sw='Weka mbali na watoto.'
    )


@pytest.fixture
def sample_batch(db, sample_product):
    from apps.products.models import Batch
    from django.utils import timezone
    from datetime import timedelta
    return Batch.objects.create(
        product=sample_product,
        batch_number='CT-BATCH-2026-001',
        manufacture_date=timezone.now().date() - timedelta(days=30),
        expiry_date=timezone.now().date() + timedelta(days=365),
        total_quantity=500
    )


@pytest.fixture
def sample_unit_code(db, sample_batch):
    from apps.products.models import UnitCode
    secure_code, hmac_sig = UnitCode.generate_hmac_code(str(sample_batch.id), 'CT-SER-0001')
    return UnitCode.objects.create(
        batch=sample_batch,
        serial_number='CT-SER-0001',
        secure_code=secure_code,
        hmac_signature=hmac_sig,
        scan_count=0
    )
