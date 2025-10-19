from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-tw9o&ao7_0y!(@nkok_7$pd0ye2oq%rnr58&$m8ay$ly5&r2gs'

# Habilite DEBUG durante desenvolvimento local; em produção, defina como False e use ALLOWED_HOSTS apropriado.
DEBUG = True

# Adicione o IP do seu servidor Ubuntu (192.168.0.100) e localhost para evitar Bad Request/DisallowedHost
ALLOWED_HOSTS = [
    '192.168.0.100', 'localhost', '127.0.0.1',
    '10.5.1.163', '45.168.147.205'  # IP local do Ubuntu Server
]
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/ecomonitoramento/static/'
# Garante que o Django encontre o diretório `static/` no projeto durante desenvolvimento
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = '/var/www/ecomonitoramento/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
