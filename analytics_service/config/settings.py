"""
Django settings for Analytics Service.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = BASE_DIR.parent
sys.path.insert(0, str(SHARED_DIR))

# Load root .env file
load_dotenv(SHARED_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY', 'analytics-service-dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'dashboard.apps.DashboardConfig',
    'forecasting.apps.ForecastingConfig',
    'credit_score.apps.CreditScoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database - SQLite for dev, PostgreSQL (Supabase) for prod via DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,  # Disable SSL for local development (DEBUG=True)
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = DEBUG

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'shared.authentication.JWTServiceAuthentication',
        'shared.authentication.ServiceToServiceAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'shared.permissions.IsAuthenticatedUser',
    ),
    'EXCEPTION_HANDLER': 'shared.exceptions.custom_exception_handler',
}

SERVICE_SECRET_KEY = os.environ.get('SERVICE_SECRET_KEY', 'ledgermind-service-secret-dev')
TRANSACTION_SERVICE_URL = os.environ.get('TRANSACTION_SERVICE_URL', 'http://localhost:8002')

# Redis Cache configuration.
# REDIS_URL uses database index /3 for analytics (matches docker-compose.yml).
# KEY_PREFIX namespaces all keys from this service so they never collide
# with keys from other services that might share the same Redis instance.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/3'),
        "TIMEOUT": 300,  # Default TTL: 5 minutes (individual views can override)
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Degrade gracefully if Redis is down
        },
        "KEY_PREFIX": "analytics",  # All keys look like: analytics:dashboard:transactions:...
    }
}
