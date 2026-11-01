from rest_framework import serializers
from .models import Pharmacy, InventoryItem
from apps.products.serializers import BatchSerializer

class PharmacySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy
        fields = '__all__'

class InventoryItemSerializer(serializers.ModelSerializer):
    batch_details = BatchSerializer(source='batch', read_only=True)
    is_expired = serializers.ReadOnlyField(source='batch.is_expired')
    is_recalled = serializers.ReadOnlyField(source='batch.is_recalled')

    class Meta:
        model = InventoryItem
        fields = '__all__'

class AddStockByCodeSerializer(serializers.Serializer):
    secure_code_or_batch = serializers.CharField(max_length=150)
    quantity = serializers.IntegerField(min_value=1, default=10)
    purchase_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
