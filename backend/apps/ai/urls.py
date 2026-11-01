from django.urls import path

from .views import MedicineChatAPIView, PackOCRAPIView

urlpatterns = [
    path('ocr/pack/', PackOCRAPIView.as_view(), name='pack_ocr'),
    path('chat/', MedicineChatAPIView.as_view(), name='medicine_chat'),
]
