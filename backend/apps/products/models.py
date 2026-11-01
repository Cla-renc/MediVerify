import uuid
import hmac
import hashlib
from django.db import models
from django.conf import settings
from django.utils import timezone

class Manufacturer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='manufacturer_profile', null=True, blank=True)
    name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100, default='Kenya')
    contact_email = models.EmailField()
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (License: {self.license_number})"

class Product(models.Model):
    DOSAGE_CHOICES = (
        ('Tablet', 'Tablet'),
        ('Capsule', 'Capsule'),
        ('Syrup', 'Syrup / Oral Liquid'),
        ('Injection', 'Injection / IV'),
        ('Ointment', 'Ointment / Cream'),
        ('Inhaler', 'Inhaler'),
        ('Eye Drops', 'Eye Drops'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='products')
    brand_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=50, choices=DOSAGE_CHOICES, default='Tablet')
    strength = models.CharField(max_length=100, help_text="e.g., 500mg, 10mg/5ml")
    category = models.CharField(max_length=100, default='Analgesic')
    
    # Information in English
    usage_instructions_en = models.TextField(help_text="Usage instructions in English")
    side_effects_en = models.TextField(help_text="Common side effects in English")
    key_warnings_en = models.TextField(help_text="Important warnings in English")

    # Information in Swahili
    usage_instructions_sw = models.TextField(help_text="Maelezo ya matumizi kwa Kiswahili")
    side_effects_sw = models.TextField(help_text="Madhara ya kawaida kwa Kiswahili")
    key_warnings_sw = models.TextField(help_text="Tahadhari muhimu kwa Kiswahili")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand_name} ({self.generic_name} {self.strength})"

class Batch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100, unique=True)
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    total_quantity = models.PositiveIntegerField(default=100)
    is_recalled = models.BooleanField(default=False)
    recall_reason = models.TextField(blank=True, null=True)
    recalled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.batch_number} - {self.product.brand_name}"

    @property
    def is_expired(self):
        return timezone.now().date() > self.expiry_date

class UnitCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='unit_codes')
    serial_number = models.CharField(max_length=100)
    secure_code = models.CharField(max_length=120, unique=True, db_index=True)
    hmac_signature = models.CharField(max_length=64)
    scan_count = models.PositiveIntegerField(default=0)
    is_flagged_clone = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'serial_number')

    def __str__(self):
        return self.secure_code

    @classmethod
    def generate_hmac_code(cls, batch_id, serial_number):
        secret = getattr(settings, 'HMAC_SECRET_KEY', 'default-hmac-key').encode('utf-8')
        raw_msg = f"{batch_id}:{serial_number}".encode('utf-8')
        sig = hmac.new(secret, raw_msg, hashlib.sha256).hexdigest()[:12].upper()
        # Secure code format: MV-[SERIAL]-[HMAC_SIG]
        code = f"MV-{serial_number}-{sig}"
        return code, sig
