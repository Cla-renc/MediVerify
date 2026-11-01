from django.contrib import admin

from .models import AIActionAudit, ChatQuestionLog, CloneEvaluationCase, CloneModelVersion, MedicineInfo


@admin.register(CloneModelVersion)
class CloneModelVersionAdmin(admin.ModelAdmin):
    list_display = ('version', 'trained_at', 'training_samples')
    readonly_fields = ('version', 'trained_at', 'training_samples', 'model_path', 'feature_baseline', 'training_report')


@admin.register(CloneEvaluationCase)
class CloneEvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ('unit_code', 'attack_type', 'created_at')
    list_filter = ('attack_type',)


@admin.register(MedicineInfo)
class MedicineInfoAdmin(admin.ModelAdmin):
    list_display = ('generic_name', 'is_sample', 'source', 'reviewed_by', 'reviewed_date')
    list_filter = ('is_sample',)
    search_fields = ('generic_name', 'brand_names')
    fieldsets = (
        (None, {'fields': ('generic_name', 'brand_names', 'is_sample')}),
        ('English information', {'fields': ('uses_en', 'usual_use_en', 'side_effects_en', 'warnings_en', 'storage_en', 'see_doctor_en')}),
        ('Swahili information', {'fields': ('uses_sw', 'usual_use_sw', 'side_effects_sw', 'warnings_sw', 'storage_sw', 'see_doctor_sw')}),
        ('Review', {'fields': ('source', 'reviewed_by', 'reviewed_date')}),
    )


@admin.register(ChatQuestionLog)
class ChatQuestionLogAdmin(admin.ModelAdmin):
    list_display = ('language', 'question_category', 'created_at')
    readonly_fields = ('language', 'question_category', 'created_at')


@admin.register(AIActionAudit)
class AIActionAuditAdmin(admin.ModelAdmin):
    list_display = ('action', 'outcome', 'actor', 'created_at')
    readonly_fields = ('actor', 'action', 'outcome', 'details', 'created_at')
