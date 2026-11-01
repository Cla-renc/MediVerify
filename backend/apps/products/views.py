from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone

from .models import Manufacturer, Product, Batch, UnitCode
from .serializers import ManufacturerSerializer, ProductSerializer, BatchSerializer, UnitCodeSerializer
from .utils import generate_batch_qr_pdf, generate_batch_csv

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.role == 'MANUFACTURER':
            if hasattr(user, 'manufacturer_profile'):
                return qs.filter(manufacturer=user.manufacturer_profile)
        return qs

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all().order_by('-created_at')
    serializer_class = BatchSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def generate_codes(self, request, pk=None):
        batch = self.get_object()
        quantity = int(request.data.get('quantity', batch.total_quantity or 50))
        
        created_codes = []
        for i in range(1, quantity + 1):
            serial = f"SER-{batch.batch_number[-6:]}-{i:04d}"
            secure_code, hmac_sig = UnitCode.generate_hmac_code(str(batch.id), serial)
            uc, _ = UnitCode.objects.get_or_create(
                batch=batch,
                serial_number=serial,
                defaults={
                    'secure_code': secure_code,
                    'hmac_signature': hmac_sig
                }
            )
            created_codes.append(uc)

        return Response({
            "message": f"Successfully generated {len(created_codes)} HMAC unit codes for batch {batch.batch_number}.",
            "batch_number": batch.batch_number,
            "total_unit_codes": batch.unit_codes.count()
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        batch = self.get_object()
        unit_codes = batch.unit_codes.all()
        if not unit_codes.exists():
            # Generate default codes if none exist
            for i in range(1, 25):
                serial = f"SER-{batch.batch_number[-6:]}-{i:04d}"
                secure_code, hmac_sig = UnitCode.generate_hmac_code(str(batch.id), serial)
                UnitCode.objects.get_or_create(batch=batch, serial_number=serial, defaults={'secure_code': secure_code, 'hmac_signature': hmac_sig})
            unit_codes = batch.unit_codes.all()

        pdf_bytes = generate_batch_qr_pdf(batch, unit_codes)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="QR_Sheet_{batch.batch_number}.pdf"'
        return response

    @action(detail=True, methods=['get'])
    def export_csv(self, request, pk=None):
        batch = self.get_object()
        unit_codes = batch.unit_codes.all()
        csv_content = generate_batch_csv(batch, unit_codes)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="UnitCodes_{batch.batch_number}.csv"'
        return response

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def recall(self, request, pk=None):
        batch = self.get_object()
        reason = request.data.get('reason', 'Quality recall issued by manufacturer/regulator.')
        
        batch.is_recalled = True
        batch.recall_reason = reason
        batch.recalled_at = timezone.now()
        batch.save()

        return Response({
            "message": f"Batch {batch.batch_number} has been officially RECALLED.",
            "batch_number": batch.batch_number,
            "recalled_at": batch.recalled_at,
            "reason": reason
        }, status=status.HTTP_200_OK)
