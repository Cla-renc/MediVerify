from datetime import timedelta
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Q

from .models import Pharmacy, InventoryItem
from .serializers import PharmacySerializer, InventoryItemSerializer, AddStockByCodeSerializer
from apps.products.models import Batch, UnitCode

class PharmacyViewSet(viewsets.ModelViewSet):
    queryset = Pharmacy.objects.all().order_by('-trust_score')
    serializer_class = PharmacySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def trust_ratings(self, request):
        pharmacies = Pharmacy.objects.all().order_by('-trust_score')
        serializer = self.get_serializer(pharmacies, many=True)
        return Response(serializer.data)

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by('-added_at')
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'pharmacy_profile'):
            return InventoryItem.objects.filter(pharmacy=user.pharmacy_profile)
        return InventoryItem.objects.all()

    @action(detail=False, methods=['post'])
    def add_by_code(self, request):
        serializer = AddStockByCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code_input = serializer.validated_data['secure_code_or_batch'].strip()
        quantity = serializer.validated_data['quantity']
        p_price = serializer.validated_data['purchase_price']
        s_price = serializer.validated_data['selling_price']
        supplier = serializer.validated_data.get('supplier_name', 'Direct Distributor')

        user = request.user
        if not hasattr(user, 'pharmacy_profile'):
            pharmacy, _ = Pharmacy.objects.get_or_create(
                user=user,
                defaults={'name': f"{user.username}'s Pharmacy", 'license_number': f"LIC-{user.username}"}
            )
        else:
            pharmacy = user.pharmacy_profile

        # Find batch by batch_number or UnitCode secure_code
        batch = None
        if code_input.startswith("MV-") or "SER-" in code_input:
            try:
                uc = UnitCode.objects.get(secure_code__iexact=code_input)
                batch = uc.batch
            except UnitCode.DoesNotExist:
                pass

        if not batch:
            try:
                batch = Batch.objects.get(batch_number__iexact=code_input)
            except Batch.DoesNotExist:
                return Response(
                    {"error": f"No batch or unit code matching '{code_input}' was found in MediVerify registry."},
                    status=status.HTTP_404_NOT_FOUND
                )

        item, created = InventoryItem.objects.get_or_create(
            pharmacy=pharmacy,
            batch=batch,
            defaults={
                'quantity': quantity,
                'purchase_price': p_price,
                'selling_price': s_price,
                'supplier_name': supplier
            }
        )
        if not created:
            item.quantity += quantity
            item.purchase_price = p_price or item.purchase_price
            item.selling_price = s_price or item.selling_price
            item.save()

        return Response({
            "message": f"Successfully added {quantity} units of {batch.product.brand_name} (Batch: {batch.batch_number}) to inventory.",
            "inventory_item": InventoryItemSerializer(item).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def alerts_and_expiry(self, request):
        user = request.user
        if hasattr(user, 'pharmacy_profile'):
            pharmacy = user.pharmacy_profile
            items = InventoryItem.objects.filter(pharmacy=pharmacy)
        else:
            items = InventoryItem.objects.all()

        today = timezone.now().date()
        in_30_days = today + timedelta(days=30)
        in_60_days = today + timedelta(days=60)
        in_90_days = today + timedelta(days=90)

        expired_items = items.filter(batch__expiry_date__lt=today)
        expiring_30 = items.filter(batch__expiry_date__gte=today, batch__expiry_date__lte=in_30_days)
        expiring_60 = items.filter(batch__expiry_date__gt=in_30_days, batch__expiry_date__lte=in_60_days)
        expiring_90 = items.filter(batch__expiry_date__gt=in_60_days, batch__expiry_date__lte=in_90_days)
        recalled_items = items.filter(batch__is_recalled=True)
        low_stock_items = items.filter(quantity__lt=10)

        return Response({
            "summary": {
                "total_items": items.count(),
                "total_units": items.aggregate(total=Sum('quantity'))['total'] or 0,
                "expired_count": expired_items.count(),
                "expiring_30_days_count": expiring_30.count(),
                "expiring_60_days_count": expiring_60.count(),
                "expiring_90_days_count": expiring_90.count(),
                "recalled_count": recalled_items.count(),
                "low_stock_count": low_stock_items.count(),
            },
            "recalled_alerts": InventoryItemSerializer(recalled_items, many=True).data,
            "expired": InventoryItemSerializer(expired_items, many=True).data,
            "expiring_30_days": InventoryItemSerializer(expiring_30, many=True).data,
            "expiring_60_days": InventoryItemSerializer(expiring_60, many=True).data,
            "expiring_90_days": InventoryItemSerializer(expiring_90, many=True).data,
            "low_stock": InventoryItemSerializer(low_stock_items, many=True).data,
        })
