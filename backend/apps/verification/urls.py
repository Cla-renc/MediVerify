from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VerifyCodeAPIView, CloneAlertViewSet, CloneModelAPIView

router = DefaultRouter()
router.register(r'clones/alerts', CloneAlertViewSet, basename='clone_alert')

urlpatterns = [
    path('', VerifyCodeAPIView.as_view(), name='verify_code'),
    path('clones/model/', CloneModelAPIView.as_view(), name='clone_model'),
    path('', include(router.urls)),
]
