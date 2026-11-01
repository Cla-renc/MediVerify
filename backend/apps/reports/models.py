import uuid
from django.db import models
from apps.products.models import UnitCode
from apps.inventory.models import Pharmacy

class SuspiciousReport(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('INVESTIGATING', 'Under Investigation'),
        ('RESOLVED', 'Resolved / Action Taken'),
        ('REJECTED', 'Rejected / Invalid'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_code = models.ForeignKey(UnitCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.SET_NULL, null=True, blank=True, related_name='suspicious_reports')
    reporter_name = models.CharField(max_length=150, blank=True, default='Anonymous Citizen')
    reporter_phone = models.CharField(max_length=50, blank=True, null=True)
    product_name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='suspicious_reports/', blank=True, null=True)
    
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    county = models.CharField(max_length=100, default='Nairobi')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report #{str(self.id)[:8]} - {self.product_name} ({self.county})"

class SystemSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    max_scan_threshold = models.PositiveIntegerField(default=3, help_text="Number of scans before flagging high frequency")
    max_velocity_kmh = models.FloatField(default=800.0, help_text="Max impossible travel speed in km/h")
    distinct_ip_window_minutes = models.PositiveIntegerField(default=15, help_text="Window in minutes for distinct IP check")
    distinct_ip_threshold = models.PositiveIntegerField(default=3, help_text="Threshold of distinct IPs in window")
    
    # Risk Engine Weights (Summing to 1.0)
    weight_frequency = models.FloatField(default=0.35)
    weight_velocity = models.FloatField(default=0.45)
    weight_entropy = models.FloatField(default=0.20)

    ml_enabled = models.BooleanField(default=True)
    rule_weight = models.FloatField(default=0.60)
    ml_weight = models.FloatField(default=0.40)
    ml_threshold = models.FloatField(default=60.0)
    hybrid_threshold = models.FloatField(default=60.0)
    ocr_enabled = models.BooleanField(default=True)
    chatbot_enabled = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MediVerify Clone Detection Engine Settings (Scan Limit: {self.max_scan_threshold}, Max Speed: {self.max_velocity_kmh} km/h)"

    @classmethod
    def get_settings(cls):
        import uuid as _uuid
        obj, created = cls.objects.get_or_create(id=_uuid.UUID('00000000-0000-0000-0000-000000000001'))
        return obj
