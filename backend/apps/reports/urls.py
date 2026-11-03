from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SuspiciousReportViewSet, HeatmapDataAPIView, SystemSettingsAPIView, PublicStatisticsAPIView

router = DefaultRouter()
router.register(r'suspicious', SuspiciousReportViewSet, basename='suspicious_report')

urlpatterns = [
    path('stats/', PublicStatisticsAPIView.as_view(), name='public_statistics'),
    path('heatmap/', HeatmapDataAPIView.as_view(), name='heatmap_data'),
    path('settings/', SystemSettingsAPIView.as_view(), name='system_settings'),
    path('', include(router.urls)),
]
