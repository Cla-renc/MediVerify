from django.urls import path
from .views import USSDCallbackAPIView, SMSCallbackAPIView

urlpatterns = [
    path('ussd/', USSDCallbackAPIView.as_view(), name='gateway_ussd'),
    path('sms/', SMSCallbackAPIView.as_view(), name='gateway_sms'),
]
