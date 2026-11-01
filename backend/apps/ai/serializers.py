from rest_framework import serializers


class PackOCRRequestSerializer(serializers.Serializer):
    image = serializers.ImageField()


class OCRValueSerializer(serializers.Serializer):
    value = serializers.CharField(allow_null=True)
    confidence = serializers.FloatField()


class OCRRegistryMatchSerializer(serializers.Serializer):
    batch_number = serializers.CharField()
    product = serializers.CharField()
    generic_name = serializers.CharField()


class PackOCRResponseSerializer(serializers.Serializer):
    raw_text = serializers.CharField()
    batch_number = OCRValueSerializer()
    expiry_date = OCRValueSerializer()
    manufacturing_date = OCRValueSerializer()
    processing_ms = serializers.FloatField()
    registry_match = OCRRegistryMatchSerializer(allow_null=True)


class ChatRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=150)
    question = serializers.CharField(max_length=1000, trim_whitespace=True)
    language = serializers.ChoiceField(choices=('en', 'sw'), required=False)
    medicine = serializers.CharField(max_length=100, required=False, allow_blank=False)


class ChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    language = serializers.ChoiceField(choices=('en', 'sw'))
    emergency = serializers.BooleanField()
