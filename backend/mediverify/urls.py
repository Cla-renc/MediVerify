from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/pharmacy/', include('apps.inventory.urls')),
    path('api/v1/verify/', include('apps.verification.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/gateway/', include('apps.gateway.urls')),
    path('api/v1/ai/', include('apps.ai.urls')),
    path('api/v1/', include('apps.ai.urls')),
    path('api/', include('apps.ai.urls')),

    # OpenAPI / Swagger docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
