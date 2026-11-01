from rest_framework import views, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.utils import timezone

from .models import VerificationScan, CloneAlert
from .serializers import VerificationRequestSerializer, VerificationScanSerializer, CloneAlertSerializer
from .engine import CloneDetectionEngine
from apps.products.models import UnitCode
from apps.inventory.models import Pharmacy


class VerifyEndpointThrottle(AnonRateThrottle):
    """30 requests/minute per IP for the public verification endpoint."""
    scope = 'verify_endpoint'

class VerifyCodeAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [VerifyEndpointThrottle]

    def post(self, request):
        serializer = VerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_code = serializer.validated_data['code'].strip()
        channel = serializer.validated_data.get('channel', 'WEB_QR')
        lat = serializer.validated_data.get('latitude')
        lon = serializer.validated_data.get('longitude')
        pharmacy_id = serializer.validated_data.get('pharmacy_id')
        phone_number = serializer.validated_data.get('phone_number')

        # Get IP & User Agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Lookup Pharmacy
        pharmacy = None
        if pharmacy_id:
            try:
                pharmacy = Pharmacy.objects.get(id=pharmacy_id)
            except Pharmacy.DoesNotExist:
                pass

        # Lookup Unit Code
        try:
            unit_code = UnitCode.objects.select_related('batch', 'batch__product', 'batch__product__manufacturer').get(secure_code__iexact=raw_code)
        except UnitCode.DoesNotExist:
            # Log invalid scan attempt
            VerificationScan.objects.create(
                raw_code=raw_code,
                channel=channel,
                result_status='INVALID',
                latitude=lat,
                longitude=lon,
                ip_address=ip_address,
                user_agent=user_agent,
                phone_number=phone_number,
                pharmacy=pharmacy
            )
            return Response({
                "result_status": "INVALID",
                "badge_color": "gray",
                "message_en": "INVALID MEDICINE CODE: This code was not found in the official registry. DO NOT consume this product.",
                "message_sw": "DAWA HAPA HAIPO: Nambari hii haipatikani kwenye sajili rasmi. USINYWE dawa hii.",
                "code": raw_code,
                "is_genuine": False
            }, status=status.HTTP_200_OK)

        batch = unit_code.batch
        product = batch.product
        manufacturer = product.manufacturer

        # Run Cloned Code Detection Engine
        detector = CloneDetectionEngine(
            unit_code=unit_code,
            current_lat=lat,
            current_lon=lon,
            current_ip=ip_address,
            current_ua=user_agent,
            channel=channel,
        )
        detection_result = detector.evaluate()

        # Determine Result Status Priority:
        # 1. RECALLED
        # 2. SUSPECTED_CLONE
        # 3. EXPIRED
        # 4. GENUINE
        if batch.is_recalled:
            result_status = 'RECALLED'
            badge_color = 'red'
            msg_en = f"RECALLED BATCH: This product batch ({batch.batch_number}) has been RECALLED by regulators. Reason: {batch.recall_reason or 'Safety advisory'}. Return to pharmacy immediately."
            msg_sw = f"DAWA IMEREJESHWA: Kundi hili la dawa ({batch.batch_number}) limeamriwa kurejeshwa na mamlaka rasmi. Rejesha kwa duka la dawa mara moja."
        elif detection_result['is_clone']:
            result_status = 'SUSPECTED_CLONE'
            badge_color = 'purple'
            msg_en = f"SUSPECTED CLONE / FRAUD (Risk Score: {detection_result['risk_score']}%): This code has been scanned abnormally or duplicated across multiple locations. Report to Pharmacy & Poisons Board."
            msg_sw = f"DAWA INAYOSHUKIWA KUWA YA BANDIA (Kiwango cha Hatari: {detection_result['risk_score']}%): Nambari hii imesomwa kwa njia touches / maeneo tofauti. Toa taarifa kwa PPB."
        elif batch.is_expired:
            result_status = 'EXPIRED'
            badge_color = 'amber'
            msg_en = f"EXPIRED MEDICINE: This batch expired on {batch.expiry_date}. DO NOT USE."
            msg_sw = f"DAWA IMEHARIBAKA/IMEPITWA NA WAKATI: Kundi hili lilipitwa na wakati tarehe {batch.expiry_date}. USITUMIE."
        else:
            result_status = 'GENUINE'
            badge_color = 'green'
            msg_en = f"GENUINE & SAFE: Authenticated product by {manufacturer.name}. Expiry date is {batch.expiry_date}."
            msg_sw = f"DAWA HALISI NA SALAMA: Imethibitishwa kutoka {manufacturer.name}. Tarehe ya mwisho ni {batch.expiry_date}."

        # Increment scan count on unit code
        unit_code.scan_count += 1
        if result_status == 'SUSPECTED_CLONE':
            unit_code.is_flagged_clone = True
        unit_code.save()

        # Log Verification Scan
        scan_log = VerificationScan.objects.create(
            unit_code=unit_code,
            raw_code=raw_code,
            channel=channel,
            result_status=result_status,
            latitude=lat,
            longitude=lon,
            ip_address=ip_address,
            user_agent=user_agent,
            phone_number=phone_number,
            pharmacy=pharmacy
        )

        # Create or update CloneAlert if clone suspected
        if detection_result['is_clone']:
            alert, created = CloneAlert.objects.get_or_create(
                unit_code=unit_code,
                defaults={
                    'risk_score': detection_result['risk_score'],
                    'status': 'PENDING',
                    'trigger_reasons': detection_result['reasons']
                }
            )
            if not created:
                alert.risk_score = max(alert.risk_score, detection_result['risk_score'])
                alert.trigger_reasons = list(set(alert.trigger_reasons + detection_result['reasons']))
                alert.save()

        return Response({
            "result_status": result_status,
            "badge_color": badge_color,
            "is_genuine": (result_status == 'GENUINE'),
            "message_en": msg_en,
            "message_sw": msg_sw,
            "product": {
                "brand_name": product.brand_name,
                "generic_name": product.generic_name,
                "strength": product.strength,
                "dosage_form": product.dosage_form,
                "category": product.category,
                "manufacturer": manufacturer.name,
                "manufacturer_country": manufacturer.country,
                "usage_instructions_en": product.usage_instructions_en,
                "usage_instructions_sw": product.usage_instructions_sw,
                "side_effects_en": product.side_effects_en,
                "side_effects_sw": product.side_effects_sw,
                "key_warnings_en": product.key_warnings_en,
                "key_warnings_sw": product.key_warnings_sw,
            },
            "batch": {
                "batch_number": batch.batch_number,
                "manufacture_date": str(batch.manufacture_date),
                "expiry_date": str(batch.expiry_date),
                "is_expired": batch.is_expired,
                "is_recalled": batch.is_recalled,
                "recall_reason": batch.recall_reason,
            },
            "verification_details": {
                "scan_id": str(scan_log.id),
                "scan_count": unit_code.scan_count,
                "secure_code": unit_code.secure_code,
                "scanned_at": scan_log.scanned_at,
                "risk_score": detection_result['risk_score'],
                "risk_reasons": detection_result['reasons'],
                "ml_score": detection_result['ml_score'],
            }
        }, status=status.HTTP_200_OK)


class CloneModelAPIView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.ai.clone_model.service import MODEL_FILE, latest_version

        model_version = latest_version()
        if not model_version or not MODEL_FILE.is_file():
            return Response({'available': False, 'version': None})
        return Response({
            'available': True,
            'version': model_version.version,
            'trained_at': model_version.trained_at,
            'training_samples': model_version.training_samples,
            'training_report': model_version.training_report,
        })

    def post(self, request):
        from apps.ai.clone_model.service import train_model
        from apps.ai.models import AIActionAudit

        try:
            model_version = train_model()
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        AIActionAudit.objects.create(
            actor=request.user,
            action='clone_model_retrain',
            outcome='success',
            details={'version': model_version.version, 'training_samples': model_version.training_samples},
        )
        return Response({
            'available': True,
            'version': model_version.version,
            'trained_at': model_version.trained_at,
            'training_samples': model_version.training_samples,
            'training_report': model_version.training_report,
        }, status=status.HTTP_201_CREATED)


class CloneAlertViewSet(viewsets.ModelViewSet):
    queryset = CloneAlert.objects.all().order_by('-created_at')
    serializer_class = CloneAlertSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        action_status = request.data.get('status', 'CONFIRMED') # CONFIRMED or DISMISSED
        
        if action_status not in ['CONFIRMED', 'DISMISSED']:
            return Response({"error": "Invalid status. Choose CONFIRMED or DISMISSED."}, status=status.HTTP_400_BAD_REQUEST)

        alert.status = action_status
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()

        if action_status == 'CONFIRMED':
            alert.unit_code.is_flagged_clone = True
            alert.unit_code.save()

        return Response({
            "message": f"Clone Alert status updated to {action_status}.",
            "alert_id": str(alert.id),
            "status": alert.status
        }, status=status.HTTP_200_OK)
