"""
Run with: python manage.py shell < create_demo_users.py
OR:        python create_demo_users.py  (if DJANGO_SETTINGS_MODULE is set)
"""
import os, sys, django

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediverify.settings')
django.setup()

from apps.authentication.models import User

DEMO_USERS = [
    dict(username='regulator',     password='admin123', role='REGULATOR',    email='regulator@mediverify.ke',   is_staff=True,  is_superuser=True,  organization_name='Pharmacy & Poisons Board'),
    dict(username='cosmos_mfg',    password='pass123',  role='MANUFACTURER', email='cosmos@mediverify.ke',      is_staff=False, is_superuser=False, organization_name='Cosmos Pharmaceuticals'),
    dict(username='dawa_mfg',      password='pass123',  role='MANUFACTURER', email='dawa@mediverify.ke',        is_staff=False, is_superuser=False, organization_name='Dawa Pharmaceuticals'),
    dict(username='beta_mfg',      password='pass123',  role='MANUFACTURER', email='beta@mediverify.ke',        is_staff=False, is_superuser=False, organization_name='Beta Healthcare'),
    dict(username='nairobi_pharm', password='pass123',  role='PHARMACIST',   email='nairobi@mediverify.ke',     is_staff=False, is_superuser=False, organization_name='Nairobi Pharmacy'),
    dict(username='mombasa_pharm', password='pass123',  role='PHARMACIST',   email='mombasa@mediverify.ke',     is_staff=False, is_superuser=False, organization_name='Mombasa Pharmacy'),
]

for data in DEMO_USERS:
    pw = data.pop('password')
    user, created = User.objects.get_or_create(username=data['username'], defaults=data)
    if not created:
        for k, v in data.items():
            setattr(user, k, v)
    user.set_password(pw)
    user.save()
    print(f"{'[CREATED]' if created else '[UPDATED]'} {user.username} ({user.role})")

print("\n✅ All demo users ready!")
print("   regulator   / admin123  (Regulator/Admin)")
print("   cosmos_mfg  / pass123   (Manufacturer)")
print("   nairobi_pharm / pass123 (Pharmacist)")
