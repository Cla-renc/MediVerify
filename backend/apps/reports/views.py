from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import SuspiciousReport, SystemSettings
from .serializers import SuspiciousReportSerializer, SystemSettingsSerializer
from apps.verification.models import CloneAlert, VerificationScan
from apps.products.models import Batch, Product
from apps.inventory.models import Pharmacy


class PublicStatisticsAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        today = timezone.localdate()
        scans_today = VerificationScan.objects.filter(scanned_at__date=today)
        total_today = scans_today.count()
        genuine_today = scans_today.filter(result_status='GENUINE').count()
        return Response({
            'as_of': timezone.now(),
            'total_scans': VerificationScan.objects.count(),
            'scans_today': total_today,
            'genuine_today': genuine_today,
            'genuine_percent_today': round(genuine_today * 100 / total_today, 1) if total_today else 0,
            'clone_alerts': CloneAlert.objects.count(),
            'clone_alerts_pending': CloneAlert.objects.filter(status='PENDING').count(),
            'registered_products': Product.objects.count(),
            'registered_batches': Batch.objects.count(),
            'registered_pharmacies': Pharmacy.objects.count(),
        })

class SuspiciousReportViewSet(viewsets.ModelViewSet):
    queryset = SuspiciousReport.objects.all().order_by('-created_at')
    serializer_class = SuspiciousReportSerializer
    permission_classes = [permissions.AllowAny] # Anyone can file a report

    def create(self, request, *args, **kwargs):
        # Validate image file size and type if present
        image_file = request.FILES.get('image')
        if image_file:
            if image_file.size > 5 * 1024 * 1024: # 5MB limit
                return Response({"error": "Image file size exceeds maximum limit of 5MB."}, status=status.HTTP_400_BAD_REQUEST)
            if not image_file.content_type.startswith('image/'):
                return Response({"error": "Invalid file format. Please upload an image file (JPEG, PNG, WEBP)."}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

class HeatmapDataAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        markers = []

        # 1. Map Markers from Suspicious Reports
        reports = SuspiciousReport.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        for r in reports:
            markers.append({
                "id": f"report-{r.id}",
                "type": "SUSPICIOUS_REPORT",
                "title": f"Report: {r.product_name}",
                "description": r.description,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "county": r.county,
                "status": r.status,
                "risk_level": "HIGH" if r.status == 'PENDING' else "MEDIUM",
                "created_at": r.created_at,
                "image_url": r.image.url if r.image else None
            })

        # 2. Map Markers from Clone Alerts & Anomaly Scans
        alerts = CloneAlert.objects.select_related('unit_code', 'unit_code__batch', 'unit_code__batch__product').all()
        for a in alerts:
            scan = a.unit_code.scans.exclude(latitude__isnull=True).exclude(longitude__isnull=True).order_by('-scanned_at').first()
            if scan:
                markers.append({
                    "id": f"clone-{a.id}",
                    "type": "CLONE_ALERT",
                    "title": f"Clone Alert: {a.unit_code.batch.product.brand_name}",
                    "description": f"Risk Score: {a.risk_score}%. {', '.join(a.trigger_reasons)}",
                    "latitude": scan.latitude,
                    "longitude": scan.longitude,
                    "county": "Anomaly Location",
                    "status": a.status,
                    "risk_level": "CRITICAL" if a.risk_score >= 80 else "HIGH",
                    "created_at": a.created_at,
                    "image_url": None
                })

        return Response({
            "total_markers": len(markers),
            "markers": markers
        }, status=status.HTTP_200_OK)

class SystemSettingsAPIView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def post(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
