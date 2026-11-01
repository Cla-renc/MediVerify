import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('MANUFACTURER', 'Manufacturer'),
        ('PHARMACIST', 'Pharmacist'),
        ('REGULATOR', 'Regulator/Admin'),
        ('PUBLIC', 'Public Customer'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PUBLIC')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    organization_name = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
