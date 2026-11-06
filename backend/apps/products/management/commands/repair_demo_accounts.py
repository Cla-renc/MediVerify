from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.inventory.models import Pharmacy
from apps.products.models import Manufacturer


MANUFACTURERS = (
    ('cosmos_mfg', 'MFG-PPB-COSMOS_MFG', 'Cosmos Limited Kenya', 'info@cosmos-pharm.co.ke'),
    ('dawa_mfg', 'MFG-PPB-DAWA_MFG', 'Dawa Pharmaceuticals Ltd', 'contact@dawa.co.ke'),
    ('beta_mfg', 'MFG-PPB-BETA_MFG', 'Beta Healthcare International', 'support@betaheadcare.co.ke'),
)

PHARMACIES = (
    ('nairobi_pharm', 'P1001', 'Nairobi City Pharmacy', 'Kenyatta Ave, CBD', 'Nairobi', -1.286389, 36.817223, 98.0, 'TRUSTED'),
    ('mombasa_pharm', 'P1002', 'Coast Medical Supplies', 'Nkrumah Rd, Town', 'Mombasa', -4.043477, 39.668206, 92.0, 'TRUSTED'),
    ('kisumu_pharm', 'P1003', 'Lakeside Chemist', 'Odinga Oginga Rd', 'Kisumu', -0.091702, 34.767956, 75.0, 'WATCH'),
    ('nakuru_pharm', 'P1004', 'Rift Valley Pharmacy', 'Kenyatta Ave', 'Nakuru', -0.303099, 36.080026, 96.0, 'TRUSTED'),
    ('eldoret_pharm', 'P1005', 'Highland Healthcare', 'Uganda Rd', 'Uasin Gishu', 0.514277, 35.269780, 42.0, 'FLAGGED'),
)


class Command(BaseCommand):
    help = 'Repair roles and demo profiles for existing seeded accounts without reseeding data.'

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        try:
            regulator = User.objects.get(username='regulator')
        except User.DoesNotExist as exc:
            raise CommandError('Seeded regulator account "regulator" was not found.') from exc

        regulator.role = 'REGULATOR'
        regulator.is_active = True
        regulator.is_staff = True
        regulator.is_superuser = True
        regulator.save(update_fields=['role', 'is_active', 'is_staff', 'is_superuser'])
        self.stdout.write('Repaired regulator account.')

        for username, license_number, name, email in MANUFACTURERS:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f'Seeded manufacturer account "{username}" was not found.') from exc
            user.role = 'MANUFACTURER'
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.organization_name = name
            user.save(update_fields=['role', 'is_active', 'is_staff', 'is_superuser', 'organization_name'])
            manufacturer = Manufacturer.objects.filter(user=user).first()
            if manufacturer is None:
                manufacturer = Manufacturer.objects.filter(license_number=license_number).first()
            if manufacturer is None:
                manufacturer = Manufacturer(license_number=license_number)
            elif manufacturer.user_id not in (None, user.pk):
                raise CommandError(f'Manufacturer license {license_number} belongs to another account.')
            manufacturer.user = user
            manufacturer.name = name
            manufacturer.country = 'Kenya'
            manufacturer.contact_email = email
            manufacturer.is_verified = True
            manufacturer.license_number = license_number
            manufacturer.save()
            self.stdout.write(f'Repaired manufacturer account "{username}".')

        for (
            username, license_number, name, address, county,
            latitude, longitude, score, rating,
        ) in PHARMACIES:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(f'Seeded pharmacist account "{username}" was not found.') from exc
            user.role = 'PHARMACIST'
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.organization_name = name
            user.save(update_fields=['role', 'is_active', 'is_staff', 'is_superuser', 'organization_name'])
            pharmacy = Pharmacy.objects.filter(user=user).first()
            if pharmacy is None:
                pharmacy = Pharmacy.objects.filter(license_number=license_number).first()
            if pharmacy is None:
                pharmacy = Pharmacy(license_number=license_number)
            elif pharmacy.user_id not in (None, user.pk):
                raise CommandError(f'Pharmacy license {license_number} belongs to another account.')
            pharmacy.user = user
            pharmacy.name = name
            pharmacy.license_number = license_number
            pharmacy.address = address
            pharmacy.county = county
            pharmacy.latitude = latitude
            pharmacy.longitude = longitude
            pharmacy.trust_score = score
            pharmacy.trust_rating = rating
            pharmacy.save()
            self.stdout.write(f'Repaired pharmacist account "{username}".')

        self.stdout.write(self.style.SUCCESS('Demo accounts repaired. Existing passwords were not changed.'))
