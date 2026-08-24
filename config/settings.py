"""Configuração do Django — Sistema MCMV (Barão de Cocais/MG).

Banco: SQLite em desenvolvimento (padrão). Para PostgreSQL em produção, basta
definir as variáveis de ambiente ``POSTGRES_DB``/``POSTGRES_USER``/etc. — nenhuma
mudança de código é necessária.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Segurança ------------------------------------------------------------- #
# Em produção, defina SECRET_KEY por variável de ambiente. O default abaixo é
# apenas para desenvolvimento e NÃO deve ir para produção.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-inseguro-troque-em-producao-por-favor"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# --- Aplicações ------------------------------------------------------------ #
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps do projeto
    "auditoria",
    "contas",
    "cadastro",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Captura o usuário/IP atual para a trilha de auditoria.
    "auditoria.middleware.UsuarioAtualMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Banco de dados -------------------------------------------------------- #
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Validação de senha ---------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalização --------------------------------------------------- #
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --- Arquivos estáticos e de mídia ----------------------------------------- #
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Documentos (dados pessoais/sensíveis) NÃO ficam sob STATIC/URL pública.
# São guardados em MEDIA_ROOT (fora da raiz web) e servidos por view autenticada.
MEDIA_ROOT = Path(os.environ.get("MCMV_MEDIA_ROOT", BASE_DIR / "media_protegida"))
MEDIA_URL = "/documentos/"  # roteado por view com checagem de permissão (Fase 3)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Sessão e segurança web ------------------------------------------------ #
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_AGE", 30 * 60))  # 30 min
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = False  # o token precisa ser lido por formulários

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Caminho dos parâmetros do edital (usado pelo motor de pontuação).
PARAMETROS_EDITAL = os.environ.get(
    "MCMV_PARAMETROS_EDITAL", str(BASE_DIR / "regras" / "parametros_edital.yaml")
)
