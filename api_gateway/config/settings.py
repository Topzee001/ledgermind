"""
Django settings for API Gateway Service.
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

SECRET_KEY = os.environ.get('SECRET_KEY', 'api-gateway-dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'corsheaders',
    'gateway.apps.GatewayConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = []
WSGI_APPLICATION = 'config.wsgi.application'

# Database - SQLite for dev, PostgreSQL (Supabase) for prod via DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
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

CORS_ALLOW_ALL_ORIGINS = True

# Service URLs mapped to their prefixes
SERVICE_MAP = {
    'users': os.environ.get('USER_SERVICE_URL', 'http://localhost:8001'),
    'businesses': os.environ.get('USER_SERVICE_URL', 'http://localhost:8001'),
    'transactions': os.environ.get('TRANSACTION_SERVICE_URL', 'http://localhost:8002'),
    'categories': os.environ.get('TRANSACTION_SERVICE_URL', 'http://localhost:8002'),
    'categorize': os.environ.get('AI_SERVICE_URL', 'http://localhost:8003'),
    'analytics': os.environ.get('ANALYTICS_SERVICE_URL', 'http://localhost:8004'),
    'payments': os.environ.get('PAYMENT_SERVICE_URL', 'http://localhost:8005'),
}
