from rest_framework import serializers
from .models import VerificationScan, CloneAlert
from apps.products.serializers import UnitCodeSerializer

class VerificationRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=150)
    channel = serializers.ChoiceField(choices=['WEB_QR', 'WEB_MANUAL', 'SMS', 'USSD'], default='WEB_QR')
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    pharmacy_id = serializers.UUIDField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_null=True)

class VerificationScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationScan
        fields = '__all__'

class CloneAlertSerializer(serializers.ModelSerializer):
    secure_code = serializers.ReadOnlyField(source='unit_code.secure_code')
    product_brand_name = serializers.ReadOnlyField(source='unit_code.batch.product.brand_name')
    batch_number = serializers.ReadOnlyField(source='unit_code.batch.batch_number')
    manufacturer_name = serializers.ReadOnlyField(source='unit_code.batch.product.manufacturer.name')

    class Meta:
        model = CloneAlert
        fields = '__all__'
