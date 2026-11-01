import uuid
from django.db import models
from django.conf import settings
from apps.products.models import UnitCode
from apps.inventory.models import Pharmacy

class VerificationScan(models.Model):
    CHANNEL_CHOICES = (
        ('WEB_QR', 'Web Camera QR'),
        ('WEB_MANUAL', 'Web Manual Entry'),
        ('SMS', 'SMS Verification'),
        ('USSD', 'USSD Verification'),
    )

    RESULT_CHOICES = (
        ('GENUINE', 'Genuine Medicine'),
        ('EXPIRED', 'Expired Medicine'),
        ('RECALLED', 'Recalled Medicine Batch'),
        ('SUSPECTED_CLONE', 'Suspected Clone Code'),
        ('INVALID', 'Not Found / Invalid Code'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_code = models.ForeignKey(UnitCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='scans')
    raw_code = models.CharField(max_length=150)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='WEB_QR')
    result_status = models.CharField(max_length=20, choices=RESULT_CHOICES)
    
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True, related_name='scans')
    
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan {self.raw_code} ({self.result_status}) via {self.channel} at {self.scanned_at.strftime('%Y-%m-%d %H:%M')}"

class CloneAlert(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Regulator Review'),
        ('CONFIRMED', 'Confirmed Clone / Fraud'),
        ('DISMISSED', 'Dismissed / False Alarm'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_code = models.ForeignKey(UnitCode, on_delete=models.CASCADE, related_name='clone_alerts')
    risk_score = models.FloatField(default=0.0, help_text="Calculated risk score 0 to 100")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    trigger_reasons = models.JSONField(default=list, help_text="List of rules and descriptions that triggered the alert")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')

    def __str__(self):
        return f"Clone Alert on {self.unit_code.secure_code} (Risk: {self.risk_score}%) - Status: {self.status}"
