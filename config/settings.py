from pathlib import Path
import os
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY should come from environment in production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-tw9o&ao7_0y!(@nkok_7$pd0ye2oq%rnr58&$m8ay$ly5&r2gs')

# DEBUG controlled by env var (default True for local dev)
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

# ALLOWED_HOSTS can be provided via comma-separated env var; sensible defaults kept for development
_default_hosts = ['127.0.0.1', 'localhost']
_env_hosts = os.getenv('DJANGO_ALLOWED_HOSTS')
if _env_hosts:
    ALLOWED_HOSTS = [h.strip() for h in _env_hosts.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = _default_hosts + ['192.168.0.100', '10.5.1.163', '45.168.147.205']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',  # seu app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
        'DIRS': [str(BASE_DIR / 'templates')],  # Garante que o caminho é string
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

# Database configuration: supports DATABASE_URL (postgres) or individual PG_* env vars, falls back to sqlite for local development
DATABASES = {}
_database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if _database_url:
    # Parse DATABASE_URL (e.g. postgres://user:pass@host:port/dbname)
    parsed = urlparse(_database_url)
    engine = 'django.db.backends.postgresql'
    DATABASES['default'] = {
        'ENGINE': engine,
        'NAME': parsed.path.lstrip('/'),
        'USER': parsed.username,
        'PASSWORD': parsed.password,
        'HOST': parsed.hostname,
        'PORT': parsed.port or 5432,
    }
else:
    # Try individual postgres vars
    if os.getenv('POSTGRES_DB') and os.getenv('POSTGRES_USER'):
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    else:
        # Fallback to sqlite for local development
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True
USE_TZ = True

# Static and media - default to project-local folders, but allow override in env
STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('DJANGO_STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
# Garante que o Django encontre o diretório `static/` no projeto durante desenvolvimento
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.getenv('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Simple logging configuration: console (for gunicorn/nginx) and rotating file in BASE_DIR/logs
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv('DJANGO_LOG_DIR', str(BASE_DIR / 'logs'))
# try to ensure the log directory exists; if not possible, continue (permission errors will raise at runtime)
try:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
except Exception:
    pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(Path(LOG_DIR) / 'django.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
