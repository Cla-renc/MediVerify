from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction

from apps.inventory.models import Pharmacy
from apps.products.models import Manufacturer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'organization_name', 'created_at')
        read_only_fields = ('id', 'created_at')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(
        choices=[
            ('PUBLIC', 'Public Customer'),
            ('MANUFACTURER', 'Manufacturer'),
            ('PHARMACIST', 'Pharmacist'),
        ],
        default='PUBLIC',
    )
    license_number = serializers.CharField(max_length=100, required=False, write_only=True)
    address = serializers.CharField(required=False, write_only=True)
    county = serializers.CharField(max_length=100, required=False, write_only=True)
    pending_approval = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'first_name', 'last_name', 'role',
            'phone_number', 'organization_name', 'license_number', 'address',
            'county', 'pending_approval',
        )
        extra_kwargs = {'email': {'required': True}}

    def validate(self, attrs):
        role = attrs.get('role', 'PUBLIC')
        if role in ('MANUFACTURER', 'PHARMACIST') and not attrs.get('license_number'):
            raise serializers.ValidationError({'license_number': 'A license number is required for this account type.'})
        if role == 'PHARMACIST' and not attrs.get('address'):
            raise serializers.ValidationError({'address': 'A pharmacy address is required.'})
        license_number = attrs.get('license_number')
        if license_number and (
            Manufacturer.objects.filter(license_number=license_number).exists()
            or Pharmacy.objects.filter(license_number=license_number).exists()
        ):
            raise serializers.ValidationError({'license_number': 'This license number is already registered.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop('role', 'PUBLIC')
        license_number = validated_data.pop('license_number', None)
        address = validated_data.pop('address', '')
        county = validated_data.pop('county', '') or 'Nairobi'
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=role,
            phone_number=validated_data.get('phone_number', ''),
            organization_name=validated_data.get('organization_name', ''),
            is_active=role == 'PUBLIC',
        )
        if role == 'MANUFACTURER':
            Manufacturer.objects.create(
                user=user,
                name=user.organization_name or user.username,
                license_number=license_number,
                contact_email=user.email,
                is_verified=False,
            )
        elif role == 'PHARMACIST':
            Pharmacy.objects.create(
                user=user,
                name=user.organization_name or user.username,
                license_number=license_number,
                address=address,
                county=county,
            )
        return user

    def get_pending_approval(self, user):
        return not user.is_active

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
