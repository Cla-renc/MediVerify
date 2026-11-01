from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PharmacyViewSet, InventoryViewSet

router = DefaultRouter()
router.register(r'pharmacies', PharmacyViewSet, basename='pharmacy')
router.register(r'stock', InventoryViewSet, basename='inventory')

urlpatterns = [
    path('', include(router.urls)),
]
