"""
Django settings for docufy_ai project.
"""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


def env_list(key, default=''):
    value = os.environ.get(key, default)
    return [item.strip() for item in value.split(',') if item.strip()]


def env_int(key, default):
    value = os.environ.get(key)
    return int(value) if value else default


def env_float(key, default):
    value = os.environ.get(key)
    return float(value) if value else default


SECRET_KEY = env('DJANGO_SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    'core',
    'documents',
    'search',
    'ask_ai',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'docufy_ai.urls'

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

WSGI_APPLICATION = 'docufy_ai.wsgi.application'
ASGI_APPLICATION = 'docufy_ai.asgi.application'

AUTH_USER_MODEL = 'core.User'

# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', 'docufy_ai'),
        'USER': env('POSTGRES_USER', 'docufy_ai'),
        'PASSWORD': env('POSTGRES_PASSWORD', 'docufy_ai'),
        'HOST': env('POSTGRES_HOST', 'localhost'),
        'PORT': env('POSTGRES_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'USER_ID_FIELD': 'id',
}

# CORS (local dev: Next.js on :3000)

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000',
)
CORS_ALLOW_CREDENTIALS = True

# File storage — MinIO (S3-compatible)

STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3.S3Storage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

AWS_ACCESS_KEY_ID = env('MINIO_ACCESS_KEY', 'docufy_minio')
AWS_SECRET_ACCESS_KEY = env('MINIO_SECRET_KEY', 'docufy_minio_secret')
AWS_STORAGE_BUCKET_NAME = env('MINIO_BUCKET_NAME', 'docufy-documents')
AWS_S3_ENDPOINT_URL = env('MINIO_ENDPOINT_URL', 'http://localhost:9000')
AWS_S3_ADDRESSING_STYLE = 'path'
AWS_S3_USE_SSL = env_bool('MINIO_USE_SSL', False)
AWS_S3_VERIFY = env_bool('MINIO_USE_SSL', False)
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600

# Celery / Redis

CELERY_BROKER_URL = env('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Document processing (Phase 2)

# Language packs to try during OCR — PaddleOCR has no single "auto" mode,
# so we run each configured language and keep the best-scoring result.
# 'en' covers Uzbek's Latin script reasonably well; there's no dedicated
# Uzbek model, so this is a best-effort approximation, not true UZ OCR.
OCR_LANGUAGES = env_list('OCR_LANGUAGES', 'en,ru')

# Search & retrieval (Phase 3)

QDRANT_URL = env('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = env('QDRANT_API_KEY', '')
QDRANT_COLLECTION_NAME = env('QDRANT_COLLECTION_NAME', 'docufy_chunks')

# BGE-M3: multilingual (100+ languages incl. Uzbek/Russian/English), 1024-dim
# dense embeddings. Loaded lazily on first use — see documents/processing/embeddings.py.
EMBEDDING_MODEL_NAME = env('EMBEDDING_MODEL_NAME', 'BAAI/bge-m3')
EMBEDDING_DIMENSION = 1024

# AI Gateway & RAG (Phase 4)

# 'anthropic' (Claude API) or 'ollama' (local model, e.g. Qwen/Gemma via
# Ollama's OpenAI-compatible endpoint) — see ai_gateway/. AI_GATEWAY_MODEL
# left blank uses each client's own sensible default.
AI_GATEWAY_PROVIDER = env('AI_GATEWAY_PROVIDER', 'anthropic')
AI_GATEWAY_API_KEY = env('AI_GATEWAY_API_KEY', '')
AI_GATEWAY_BASE_URL = env('AI_GATEWAY_BASE_URL', '')
AI_GATEWAY_MODEL = env('AI_GATEWAY_MODEL', '')

# How many chunks to retrieve per question, and the minimum similarity
# score a top result must clear before we bother asking the LLM at all
# (below this, we skip the LLM call and return the low-confidence fallback
# directly — cheaper and avoids inviting a hallucinated answer).
RAG_TOP_K = env_int('RAG_TOP_K', 5)
RAG_MIN_SCORE = env_float('RAG_MIN_SCORE', 0.3)
