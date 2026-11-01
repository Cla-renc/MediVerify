import uuid
from django.db import models
from django.conf import settings
from apps.products.models import Batch

class Pharmacy(models.Model):
    TRUST_RATING_CHOICES = (
        ('TRUSTED', 'Trusted Pharmacy'),
        ('WATCH', 'Under Watch'),
        ('FLAGGED', 'Flagged / High Risk'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacy_profile', null=True, blank=True)
    name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    county = models.CharField(max_length=100, default='Nairobi')
    latitude = models.FloatField(default=-1.286389)  # Default Nairobi
    longitude = models.FloatField(default=36.817223)
    trust_rating = models.CharField(max_length=20, choices=TRUST_RATING_CHOICES, default='TRUSTED')
    trust_score = models.FloatField(default=95.0, help_text="Dynamic score from 0.0 to 100.0")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.county}) - Rating: {self.get_trust_rating_display()}"

    def update_trust_score(self, expired_count, recalled_count, suspicious_reports_count):
        """
        Dynamically computes trust rating based on verification history,
        expired/recalled items in stock, and linked suspicious reports.
        """
        score = 100.0
        score -= (expired_count * 5.0)
        score -= (recalled_count * 15.0)
        score -= (suspicious_reports_count * 10.0)
        
        score = max(0.0, min(100.0, score))
        self.trust_score = score
        
        if score >= 80.0:
            self.trust_rating = 'TRUSTED'
        elif score >= 50.0:
            self.trust_rating = 'WATCH'
        else:
            self.trust_rating = 'FLAGGED'
            
        self.save()
        return score

class InventoryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='inventory_items')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='inventory_entries')
    quantity = models.PositiveIntegerField(default=10)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier_name = models.CharField(max_length=200, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('pharmacy', 'batch')

    def __str__(self):
        return f"{self.pharmacy.name} - {self.batch.product.brand_name} ({self.quantity} units)"
