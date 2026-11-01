from django.contrib import admin
from .models import SuspiciousReport, SystemSettings

@admin.register(SuspiciousReport)
class SuspiciousReportAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'county', 'status', 'reporter_name', 'created_at')
    list_filter = ('status', 'county', 'created_at')
    search_fields = ('product_name', 'description', 'reporter_name')

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('max_scan_threshold', 'max_velocity_kmh', 'distinct_ip_threshold', 'updated_at')
