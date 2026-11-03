from django.urls import path

from .consumers import CloneAlertConsumer

websocket_urlpatterns = [
    path('ws/clone-alerts/', CloneAlertConsumer.as_asgi()),
]
