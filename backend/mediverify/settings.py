import os
import sys
from pathlib import Path
from datetime import timedelta
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')

# Add apps directory to sys.path
sys.path.insert(0, str(BASE_DIR / 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-mediverify-super-secret-key-2026-kenya-anti-counterfeit',
)
HMAC_SECRET_KEY = os.environ.get('HMAC_SECRET_KEY', 'mediverify-hmac-secret-signature-key-998877')

if not DEBUG:
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure-'):
        raise ImproperlyConfigured('Set a random DJANGO_SECRET_KEY with at least 50 characters in production.')
    if len(HMAC_SECRET_KEY) < 32 or HMAC_SECRET_KEY == 'mediverify-hmac-secret-signature-key-998877':
        raise ImproperlyConfigured('Set a unique HMAC_SECRET_KEY with at least 32 characters in production.')

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    allowed_hosts = os.environ.get('ALLOWED_HOSTS', os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''))
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(',') if host.strip()]
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured('Set ALLOWED_HOSTS to the backend hostname(s) in production.')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party packages
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',

    # Custom apps
    'apps.authentication',
    'apps.products',
    'apps.inventory',
    'apps.verification',
    'apps.reports',
    'apps.gateway',
    'apps.ai',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mediverify.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mediverify.wsgi.application'

# Use SQLite locally and a managed PostgreSQL URL when deployed.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=True,
            ssl_require=not DEBUG,
        ),
    }
    if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
        DATABASES['default'].setdefault('OPTIONS', {})['options'] = '-c statement_timeout=15000'
        DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
elif DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    raise ImproperlyConfigured('DATABASE_URL is required when DEBUG is False.')

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static & Media Files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if not DEBUG
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '120/minute',
        'verify_endpoint': '30/minute',
        'ocr_upload': '8/minute',
        'ai_chat': '15/minute',
        'sms_info': '20/minute',
        'ussd_gateway': '120/minute',
    }
}

# SimpleJWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Configuration: keep permissive behavior for local development only.
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
if not DEBUG and (not CORS_ALLOWED_ORIGINS or '*' in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured('Set CORS_ALLOWED_ORIGINS to the frontend HTTPS origin in production.')
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Africa's Talking Settings
AFRICASTALKING_USERNAME = os.environ.get('AFRICASTALKING_USERNAME', 'sandbox')
AFRICASTALKING_API_KEY = os.environ.get('AFRICASTALKING_API_KEY', '')
AFRICASTALKING_ENABLED = os.environ.get('AFRICASTALKING_ENABLED', 'False').lower() in ('true', '1', 'yes')
AFRICASTALKING_BASE_URL = os.environ.get(
    'AFRICASTALKING_BASE_URL',
    'https://api.sandbox.africastalking.com'
    if AFRICASTALKING_USERNAME == 'sandbox'
    else 'https://api.africastalking.com',
)
AFRICASTALKING_SENDER_ID = os.environ.get('AFRICASTALKING_SENDER_ID', '')
AFRICASTALKING_CALLBACK_TOKEN = os.environ.get('AFRICASTALKING_CALLBACK_TOKEN', '')

# DRF Spectacular — OpenAPI / Swagger Settings
REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'

SPECTACULAR_SETTINGS = {
    'TITLE': 'MediVerify API',
    'DESCRIPTION': (
        'Counterfeit & Expired Medicine Verification System with Cloned-Code Detection Engine. '
        'Kenyan Pharmaceutical Market — PPB Registered.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'admin@mediverify.co.ke'},
    'LICENSE': {'name': 'MIT'},
}
