from django.contrib import admin
from .models import Manufacturer, Product, Batch, UnitCode

@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'license_number', 'country', 'contact_email', 'is_verified')
    search_fields = ('name', 'license_number', 'contact_email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('brand_name', 'generic_name', 'strength', 'dosage_form', 'manufacturer')
    list_filter = ('dosage_form', 'category', 'manufacturer')
    search_fields = ('brand_name', 'generic_name')

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'product', 'manufacture_date', 'expiry_date', 'total_quantity', 'is_recalled')
    list_filter = ('is_recalled', 'expiry_date')
    search_fields = ('batch_number', 'product__brand_name')

@admin.register(UnitCode)
class UnitCodeAdmin(admin.ModelAdmin):
    list_display = ('secure_code', 'batch', 'serial_number', 'scan_count', 'is_flagged_clone')
    list_filter = ('is_flagged_clone',)
    search_fields = ('secure_code', 'serial_number')
