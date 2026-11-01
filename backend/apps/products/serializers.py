from rest_framework import serializers
from .models import Manufacturer, Product, Batch, UnitCode

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.ReadOnlyField(source='manufacturer.name')

    class Meta:
        model = Product
        fields = '__all__'

class BatchSerializer(serializers.ModelSerializer):
    product_brand_name = serializers.ReadOnlyField(source='product.brand_name')
    product_generic_name = serializers.ReadOnlyField(source='product.generic_name')
    product_dosage_form = serializers.ReadOnlyField(source='product.dosage_form')
    product_strength = serializers.ReadOnlyField(source='product.strength')
    manufacturer_name = serializers.ReadOnlyField(source='product.manufacturer.name')
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Batch
        fields = '__all__'

class UnitCodeSerializer(serializers.ModelSerializer):
    batch_number = serializers.ReadOnlyField(source='batch.batch_number')

    class Meta:
        model = UnitCode
        fields = '__all__'
