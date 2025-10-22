from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Configurações de SEGURANÇA e HOSTS ---

# WARNING: Em produção, o ideal é ler esta chave de uma variável de ambiente (.env)
SECRET_KEY = 'django-insecure-tw9o&ao7_0y!(@nkok_7$pd0ye2oq%rnr58&$m8ay$ly5&r2gs'

# CRÍTICO: DEBUG deve ser False em produção
DEBUG = False

# CRÍTICO: Todos os IPs/Domínios que o Nginx está servindo
ALLOWED_HOSTS = [
    '10.5.1.100',  # IP do seu servidor
    'localhost',
    '127.0.0.1',
    # Adicione aqui qualquer domínio futuro ou IP externo que você for usar
]

# --- Configurações de Aplicativos e Middleware (Sem Alterações) ---

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',  # seu app
    # 'rest_framework', # Opcional se usar DRF
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

WSGI_APPLICATION = 'config.wsgi.application'

# --- CRÍTICO: Configuração do PostgreSQL para Produção ---

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ecoviewdb',              # Nome do banco de dados criado na Etapa 2
        'USER': 'ecoviewuser',            # Usuário do banco de dados criado na Etapa 2
        'PASSWORD': 'sua_senha_muito_forte', # Substitua pela SUA SENHA REAL!
        'HOST': 'localhost',
        'PORT': '',                       # Deixe em branco para o padrão (5432)
    }
}

# --- Configurações de Linguagem e Fuso Horário (Sem Alterações) ---

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True
USE_TZ = True

# --- CRÍTICO: Configurações de Arquivos Estáticos e Mídia para Nginx ---

# O Nginx servirá arquivos estáticos a partir deste caminho (collectstatic)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Diretórios estáticos que o Django usa para desenvolvimento
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Arquivos de mídia (uploads de usuário)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'