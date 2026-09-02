"""Configuração do Django — Sistema MCMV (Barão de Cocais/MG).

Banco: SQLite em desenvolvimento (padrão). Para PostgreSQL em produção, basta
definir as variáveis de ambiente ``POSTGRES_DB``/``POSTGRES_USER``/etc. — nenhuma
mudança de código é necessária.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de um arquivo .env, se python-dotenv estiver instalado.
try:  # opcional — em produção as variáveis podem vir do systemd/ambiente
    from dotenv import load_dotenv

    # encoding utf-8-sig remove um eventual BOM no início do arquivo (o Bloco de
    # Notas e o PowerShell 5.1 costumam gravar com BOM), evitando que a primeira
    # variável do .env seja lida com o caractere BOM colado no nome.
    load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")
except ImportError:
    pass


def _env_bool(nome: str, padrao: str = "0") -> bool:
    return os.environ.get(nome, padrao) == "1"

# --- Segurança ------------------------------------------------------------- #
# Em produção, defina SECRET_KEY por variável de ambiente. O default abaixo é
# apenas para desenvolvimento e NÃO deve ir para produção.
_SECRET_DEV = "dev-inseguro-troque-em-producao-por-favor"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _SECRET_DEV)
DEBUG = _env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]
# Garante o acesso local (no próprio servidor) mesmo que o operador esqueça de
# listar estes hosts — evita o erro DisallowedHost em http://127.0.0.1:8000.
for _local_host in ("127.0.0.1", "localhost"):
    if _local_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_local_host)

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Em produção, exige SECRET_KEY própria (nunca a de desenvolvimento).
if not DEBUG and SECRET_KEY == _SECRET_DEV:
    raise ImproperlyConfigured(
        "Defina DJANGO_SECRET_KEY em produção (DJANGO_DEBUG=0)."
    )

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
                "contas.context_processors.perfis",
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
            "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
            "OPTIONS": {"sslmode": os.environ.get("POSTGRES_SSLMODE", "prefer")},
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
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: serve os estáticos pela própria aplicação (útil no Windows/Waitress,
# sem depender de IIS/nginx). Ativado só em produção e se o pacote estiver instalado.
if not DEBUG:
    try:
        import whitenoise  # noqa: F401

        MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
        STORAGES = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {
                # Manifesto tolerante: um estático faltante não derruba a página (500).
                "BACKEND": "config.storage.StaticStorage"
            },
        }
    except ImportError:
        pass

# Documentos (dados pessoais/sensíveis) NÃO ficam sob STATIC/URL pública.
# São guardados em MEDIA_ROOT (fora da raiz web) e servidos por view autenticada.
MEDIA_ROOT = Path(os.environ.get("MCMV_MEDIA_ROOT", BASE_DIR / "media_protegida"))
MEDIA_URL = "/documentos/"  # roteado por view com checagem de permissão (Fase 3)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Autenticação
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "cadastro:dashboard"
LOGOUT_REDIRECT_URL = "login"

# --- Sessão e segurança web ------------------------------------------------ #
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_AGE", 60 * 60))  # 60 min
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Renova o prazo da sessão a cada requisição: o tempo é de INATIVIDADE, não um
# limite fixo desde o login. Assim um cadastro longo não "cai" no login ao salvar.
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = False  # o token precisa ser lido por formulários

# Cabeçalhos de segurança válidos em qualquer ambiente.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    # Atrás de proxy/HTTPS (nginx/IIS). Ajuste conforme a infraestrutura.
    if _env_bool("DJANGO_BEHIND_PROXY", "1"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # HTTPS por padrão. Para um teste em rede interna via HTTP (sem certificado),
    # defina DJANGO_SSL_REDIRECT=0 — desliga o redirect, os cookies "Secure" e o HSTS.
    _ssl = _env_bool("DJANGO_SSL_REDIRECT", "1")
    SECURE_SSL_REDIRECT = _ssl
    SESSION_COOKIE_SECURE = _ssl
    CSRF_COOKIE_SECURE = _ssl
    if _ssl:
        # HSTS: 0 desliga (recomendado com certificado autoassinado, para não
        # "prender" o navegador em HTTPS se o certificado expirar/mudar).
        SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", 31536000))
        if SECURE_HSTS_SECONDS > 0:
            SECURE_HSTS_INCLUDE_SUBDOMAINS = True
            SECURE_HSTS_PRELOAD = True

# Logging (console + arquivo rotacionável em produção).
_LOG_DIR = Path(os.environ.get("MCMV_LOG_DIR", BASE_DIR / "logs"))
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} [{levelname}] {name}: {message}", "style": "{"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
if not DEBUG:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOGGING["handlers"]["arquivo"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(_LOG_DIR / "mcmv.log"),
        "maxBytes": 5 * 1024 * 1024,
        "backupCount": 5,
        "formatter": "verbose",
    }
    LOGGING["root"]["handlers"].append("arquivo")

# Caminho dos parâmetros do edital (usado pelo motor de pontuação).
PARAMETROS_EDITAL = os.environ.get(
    "MCMV_PARAMETROS_EDITAL", str(BASE_DIR / "regras" / "parametros_edital.yaml")
)

# --- E-mail (envio do recibo) ---------------------------------------------- #
# Preencha DJANGO_EMAIL_HOST (e usuário/senha) no .env para ativar o envio.
# Sem host configurado, cai no backend de console (apenas imprime no log).
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("DJANGO_EMAIL_USE_TLS", "1")
EMAIL_USE_SSL = _env_bool("DJANGO_EMAIL_USE_SSL", "0")
EMAIL_TIMEOUT = int(os.environ.get("DJANGO_EMAIL_TIMEOUT", "20"))
DEFAULT_FROM_EMAIL = os.environ.get(
    "DJANGO_EMAIL_FROM", EMAIL_HOST_USER or "mcmv@baraodecocais.mg.gov.br"
)
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = os.environ.get(
        "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
    )
# Só habilita a ação de "enviar recibo" quando há SMTP configurado.
MCMV_EMAIL_ATIVO = bool(EMAIL_HOST)

# --- Backup ----------------------------------------------------------------- #
# Pasta onde os backups (banco + documentos) são gravados. Em produção, aponte
# para um disco/local seguro (idealmente fora do servidor de aplicação).
MCMV_BACKUP_DIR = Path(os.environ.get("MCMV_BACKUP_DIR", BASE_DIR / "backups"))
# Retenção (dias) — backups mais antigos são removidos automaticamente.
MCMV_BACKUP_RETENCAO_DIAS = int(os.environ.get("MCMV_BACKUP_RETENCAO_DIAS", "30"))
# Cópia adicional em outro local (ex.: pasta de rede em outro servidor). Vazio
# desativa. Para tarefa agendada (conta SYSTEM), use caminho UNC (\\servidor\...),
# pois unidades mapeadas (M:) não existem para o SYSTEM.
MCMV_BACKUP_COPIA = os.environ.get("MCMV_BACKUP_COPIA", "")
