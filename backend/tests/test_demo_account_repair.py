import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.inventory.models import Pharmacy
from apps.products.models import Manufacturer


@pytest.mark.django_db
def test_repair_demo_accounts_restores_roles_profiles_and_preserves_password():
    User = get_user_model()
    regulator = User.objects.create_user(
        username='regulator',
        password='unchanged-regulator-password',
        role='PUBLIC',
    )
    manufacturers = [
        User.objects.create_user(username=username, password='unchanged-demo-password', role='PUBLIC')
        for username in ('cosmos_mfg', 'dawa_mfg', 'beta_mfg')
    ]
    pharmacists = [
        User.objects.create_user(username=username, password='unchanged-demo-password', role='PUBLIC')
        for username in ('nairobi_pharm', 'mombasa_pharm', 'kisumu_pharm', 'nakuru_pharm', 'eldoret_pharm')
    ]

    call_command('repair_demo_accounts', verbosity=0)

    regulator.refresh_from_db()
    assert regulator.role == 'REGULATOR'
    assert regulator.is_staff is True
    assert regulator.is_superuser is True
    assert regulator.check_password('unchanged-regulator-password')
    for user in manufacturers:
        user.refresh_from_db()
        assert user.role == 'MANUFACTURER'
        assert user.is_active is True
        assert hasattr(user, 'manufacturer_profile')
        assert user.check_password('unchanged-demo-password')
    for user in pharmacists:
        user.refresh_from_db()
        assert user.role == 'PHARMACIST'
        assert user.is_active is True
        assert hasattr(user, 'pharmacy_profile')
        assert user.check_password('unchanged-demo-password')
    assert Manufacturer.objects.count() == 3
    assert Pharmacy.objects.count() == 5


@pytest.mark.django_db
def test_repair_demo_accounts_attaches_existing_unlinked_profiles():
    User = get_user_model()
    User.objects.create_user(username='regulator', password='pw', role='PUBLIC')
    manufacturer_user = User.objects.create_user(username='cosmos_mfg', password='pw', role='PUBLIC')
    Manufacturer.objects.create(
        name='Old Cosmos Name',
        license_number='MFG-PPB-COSMOS_MFG',
        contact_email='old@example.test',
    )
    for username in ('dawa_mfg', 'beta_mfg'):
        User.objects.create_user(username=username, password='pw', role='PUBLIC')
    for username in ('nairobi_pharm', 'mombasa_pharm', 'kisumu_pharm', 'nakuru_pharm', 'eldoret_pharm'):
        User.objects.create_user(username=username, password='pw', role='PUBLIC')

    call_command('repair_demo_accounts', verbosity=0)

    manufacturer_user.refresh_from_db()
    profile = Manufacturer.objects.get(license_number='MFG-PPB-COSMOS_MFG')
    assert profile.user == manufacturer_user
    assert profile.is_verified is True
