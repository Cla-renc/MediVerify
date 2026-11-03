from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _regulator_from_token(token):
    try:
        access_token = AccessToken(token)
        user_id = access_token[jwt_settings.USER_ID_CLAIM]
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except (TokenError, KeyError, get_user_model().DoesNotExist, ValueError):
        return AnonymousUser()
    if not user.is_staff or user.role != 'REGULATOR':
        return AnonymousUser()
    return user


class RegulatorJWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        offered = scope.get('subprotocols', [])
        token = next((value for value in offered if value != 'mediverify'), None)
        scope['user'] = await _regulator_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)


class WebSocketOriginMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        origin = next(
            (value.decode('latin1') for key, value in scope.get('headers', []) if key.lower() == b'origin'),
            None,
        )
        from django.conf import settings

        allowed = origin in settings.CORS_ALLOWED_ORIGINS
        if settings.DEBUG and origin:
            allowed = allowed or origin.startswith(('http://localhost:', 'http://127.0.0.1:'))
        if origin and not allowed:
            await send({'type': 'websocket.close', 'code': 4403})
            return
        return await self.app(scope, receive, send)


class CloneAlertConsumer(AsyncJsonWebsocketConsumer):
    group_name = 'clone_alerts'

    async def connect(self):
        user = self.scope.get('user', AnonymousUser())
        if not user.is_authenticated or not user.is_staff or user.role != 'REGULATOR':
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol='mediverify')
        await self.send_json({'type': 'connected'})

    async def disconnect(self, close_code):
        if self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def clone_alert(self, event):
        await self.send_json(event['payload'])
