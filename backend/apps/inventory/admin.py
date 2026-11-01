from django.contrib import admin
from .models import Pharmacy, InventoryItem

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ('name', 'license_number', 'county', 'trust_rating', 'trust_score')
    list_filter = ('trust_rating', 'county')
    search_fields = ('name', 'license_number', 'county')

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('pharmacy', 'batch', 'quantity', 'purchase_price', 'selling_price', 'added_at')
    list_filter = ('pharmacy', 'added_at')
    search_fields = ('pharmacy__name', 'batch__batch_number')
