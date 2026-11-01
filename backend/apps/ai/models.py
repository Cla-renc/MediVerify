from django.conf import settings
from django.db import models


class CloneModelVersion(models.Model):
    version = models.CharField(max_length=32, unique=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    training_samples = models.PositiveIntegerField()
    model_path = models.CharField(max_length=500)
    feature_baseline = models.JSONField(default=dict)
    training_report = models.JSONField(default=dict)

    class Meta:
        ordering = ['-trained_at']

    def __str__(self):
        return f'Clone model {self.version}'


class CloneEvaluationCase(models.Model):
    ATTACK_TYPES = (
        ('GENUINE', 'Genuine'),
        ('REPEATED', 'Repeated scans'),
        ('DISTANT', 'Distant-location clone'),
        ('NEARBY', 'Nearby-location clone'),
        ('SLOW', 'Slow low-rate clone'),
    )

    unit_code = models.OneToOneField(
        'products.UnitCode',
        on_delete=models.CASCADE,
        related_name='evaluation_case',
    )
    attack_type = models.CharField(max_length=16, choices=ATTACK_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_attack(self):
        return self.attack_type != 'GENUINE'


class MedicineInfo(models.Model):
    generic_name = models.CharField(max_length=200, db_index=True)
    brand_names = models.JSONField(default=list, blank=True)
    uses_en = models.TextField(blank=True)
    uses_sw = models.TextField(blank=True)
    usual_use_en = models.TextField(blank=True)
    usual_use_sw = models.TextField(blank=True)
    side_effects_en = models.TextField(blank=True)
    side_effects_sw = models.TextField(blank=True)
    warnings_en = models.TextField(blank=True)
    warnings_sw = models.TextField(blank=True)
    storage_en = models.TextField(blank=True)
    storage_sw = models.TextField(blank=True)
    see_doctor_en = models.TextField(blank=True)
    see_doctor_sw = models.TextField(blank=True)
    source = models.CharField(max_length=500, default='SAMPLE - must be reviewed by a pharmacist')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_medicine_info',
    )
    reviewed_date = models.DateField(null=True, blank=True)
    is_sample = models.BooleanField(default=True)

    class Meta:
        ordering = ['generic_name']
        constraints = [
            models.UniqueConstraint(fields=['generic_name'], name='ai_unique_medicine_generic_name'),
        ]

    def __str__(self):
        suffix = ' (SAMPLE)' if self.is_sample else ''
        return f'{self.generic_name}{suffix}'


class ChatQuestionLog(models.Model):
    language = models.CharField(max_length=2)
    question_category = models.CharField(max_length=40, blank=True)
    question_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class AIActionAudit(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_action_audits',
    )
    action = models.CharField(max_length=80)
    outcome = models.CharField(max_length=20)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
