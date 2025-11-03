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
# Helper to parse a postgres URL
def _parse_db_url(url):
    p = urlparse(url)
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': p.path.lstrip('/'),
        'USER': p.username,
        'PASSWORD': p.password,
        'HOST': p.hostname,
        'PORT': p.port or 5432,
    }

# Default / primary database (can be sqlite or postgres)
_default_db = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
if _default_db:
    DATABASES['default'] = _parse_db_url(_default_db)
else:
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
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }

# --- Additional monitoring-specific databases ---
# You can provide DATABASE_URL_BRISE and DATABASE_URL_PAVIMENTOS (or individual PG_* vars suffixed)
_database_brise = os.getenv('DATABASE_URL_BRISE') or os.getenv('POSTGRES_URL_BRISE')
if _database_brise:
    DATABASES['brise'] = _parse_db_url(_database_brise)
else:
    # Optional: allow specifying parts
    if os.getenv('POSTGRES_DB_BRISE') and os.getenv('POSTGRES_USER_BRISE'):
        DATABASES['brise'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB_BRISE'),
            'USER': os.getenv('POSTGRES_USER_BRISE'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD_BRISE', ''),
            'HOST': os.getenv('POSTGRES_HOST_BRISE', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT_BRISE', '5432'),
        }

_database_pav = os.getenv('DATABASE_URL_PAVIMENTOS') or os.getenv('POSTGRES_URL_PAVIMENTOS')
if _database_pav:
    DATABASES['pavimentos'] = _parse_db_url(_database_pav)
else:
    if os.getenv('POSTGRES_DB_PAVIMENTOS') and os.getenv('POSTGRES_USER_PAVIMENTOS'):
        DATABASES['pavimentos'] = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB_PAVIMENTOS'),
            'USER': os.getenv('POSTGRES_USER_PAVIMENTOS'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD_PAVIMENTOS', ''),
            'HOST': os.getenv('POSTGRES_HOST_PAVIMENTOS', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT_PAVIMENTOS', '5432'),
        }

# Register DB router to route sensor models to specific databases
DATABASE_ROUTERS = ['app.dbrouters.MonitoringRouter']

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
