import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediverify.settings')

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter

from apps.verification.consumers import RegulatorJWTAuthMiddleware, WebSocketOriginMiddleware
from apps.verification.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': WebSocketOriginMiddleware(
        RegulatorJWTAuthMiddleware(URLRouter(websocket_urlpatterns))
    ),
})
