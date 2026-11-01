from rest_framework import serializers
from .models import SuspiciousReport, SystemSettings

class SuspiciousReportSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.ReadOnlyField(source='pharmacy.name')
    secure_code = serializers.ReadOnlyField(source='unit_code.secure_code')

    class Meta:
        model = SuspiciousReport
        fields = '__all__'

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = '__all__'

    def validate(self, attrs):
        rule_weight = attrs.get('rule_weight', getattr(self.instance, 'rule_weight', 0.6))
        ml_weight = attrs.get('ml_weight', getattr(self.instance, 'ml_weight', 0.4))
        if rule_weight < 0 or ml_weight < 0 or abs(rule_weight + ml_weight - 1.0) > 0.001:
            raise serializers.ValidationError('Rule and ML weights must be non-negative and sum to 1.0.')
        for field in ('ml_threshold', 'hybrid_threshold'):
            value = attrs.get(field, getattr(self.instance, field, 60.0))
            if not 0 <= value <= 100:
                raise serializers.ValidationError({field: 'Threshold must be between 0 and 100.'})
        return attrs
