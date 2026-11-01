from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ManufacturerViewSet, ProductViewSet, BatchViewSet

router = DefaultRouter()
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')
router.register(r'catalog', ProductViewSet, basename='product')
router.register(r'batches', BatchViewSet, basename='batch')

urlpatterns = [
    path('', include(router.urls)),
]
