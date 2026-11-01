from django.contrib import admin
from .models import VerificationScan, CloneAlert

@admin.register(VerificationScan)
class VerificationScanAdmin(admin.ModelAdmin):
    list_display = ('raw_code', 'result_status', 'channel', 'scanned_at', 'ip_address')
    list_filter = ('result_status', 'channel', 'scanned_at')
    search_fields = ('raw_code', 'ip_address', 'phone_number')

@admin.register(CloneAlert)
class CloneAlertAdmin(admin.ModelAdmin):
    list_display = ('unit_code', 'risk_score', 'status', 'created_at', 'resolved_by')
    list_filter = ('status', 'created_at')
    search_fields = ('unit_code__secure_code',)
