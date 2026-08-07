"""
Configurações do SIGTRANS Saúde.

Sistema de Gestão de Transporte de Pacientes
Prefeitura Municipal de Barão de Cocais / MG
Departamento de Informática e Tecnologia
"""
from pathlib import Path
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Execução da suíte de testes (mantém defaults amigáveis a testes).
TESTING = "test" in sys.argv


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


# --- Segurança ---------------------------------------------------------------
# Desenvolvimento assume DEBUG=True; produção DEVE definir DEBUG=False no .env.
DEBUG = env_bool("DEBUG", True)

# SECRET_KEY: em produção (DEBUG=False) é obrigatório definir por ambiente.
# Em desenvolvimento, usa uma chave efêmera apenas para não travar o boot.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG and not TESTING:
        raise RuntimeError(
            "SECRET_KEY não definida. Configure a variável de ambiente SECRET_KEY "
            "em produção (veja .env.example)."
        )
    SECRET_KEY = "dev-inseguro-somente-para-desenvolvimento-nao-use-em-producao"

# Em produção o ALLOWED_HOSTS deve ser explícito; nunca usar "*" por padrão.
_hosts_default = "localhost,127.0.0.1" if DEBUG else ""
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", _hosts_default).split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# --- Aplicações --------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Terceiros
    "rest_framework",
    "simple_history",
    # Apps do sistema
    "apps.core",
    "apps.accounts",
    "apps.pacientes",
    "apps.destinos",
    "apps.agendamentos",
    "apps.senhas",
    "apps.relatorios",
    "apps.auditoria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Encerra a sessão por inatividade (LGPD)
    "apps.core.middleware.IdleTimeoutMiddleware",
    # Restringe o perfil de recepção à área de senhas
    "apps.core.middleware.RestricaoPerfilMiddleware",
    # Auditoria: registra o usuário responsável por cada alteração
    "simple_history.middleware.HistoryRequestMiddleware",
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
                "apps.core.context_processors.branding",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Banco de dados ----------------------------------------------------------
# Produção: PostgreSQL (variáveis POSTGRES_*). Desenvolvimento: SQLite (padrão).
if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Autenticação ------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.SenhaForteValidator"},
]

# Logout automático por inatividade e bloqueio por tentativas de login (LGPD).
IDLE_TIMEOUT_SECONDS = int(os.getenv("IDLE_TIMEOUT_SECONDS", str(30 * 60)))
LOGIN_MAX_TENTATIVAS = int(os.getenv("LOGIN_MAX_TENTATIVAS", "5"))
LOGIN_BLOQUEIO_SEGUNDOS = int(os.getenv("LOGIN_BLOQUEIO_SEGUNDOS", str(15 * 60)))

SECURE_REFERRER_POLICY = "same-origin"

# Bloqueio por inatividade (LGPD): expira a sessão após o tempo definido.
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", str(30 * 60)))  # 30 min
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# --- Internacionalização -----------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --- Arquivos estáticos ------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Em produção usa WhiteNoise (comprimido + versionado); em dev/testes usa o
# storage padrão, evitando a exigência de manifesto (collectstatic).
_staticfiles_backend = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if (DEBUG or TESTING)
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": _staticfiles_backend},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Segurança em produção ---------------------------------------------------
if not DEBUG and not TESTING:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# --- REST Framework (base para integrações futuras) --------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# --- Parâmetros do SIGTRANS (usados a partir da Fase 2) ----------------------
# Janela de atendimento da agenda e dias úteis.
SIGTRANS = {
    "AGENDA_HORA_INICIO": os.getenv("AGENDA_HORA_INICIO", "05:00"),
    "AGENDA_HORA_FIM": os.getenv("AGENDA_HORA_FIM", "18:00"),
    "AGENDA_DIAS_UTEIS": [0, 1, 2, 3, 4],  # 0=segunda ... 4=sexta
    "AGENDA_LIMITE_DIARIO": None,  # None = sem limite diário de agendamentos
    "SENHA_MAX": 50,          # senhas de 01 a 50, reiniciando em seguida
    "SENHA_SALA_LABEL": "Sala",
    # Filas de senha: cada fila tem prefixo, sala fixa e nome próprios, com
    # numeração independente. Para incluir/remover salas, edite este dicionário.
    "SENHA_FILAS": {
        "CONSULTAS": {"prefixo": "MC", "sala": 1, "nome": "Marcação de Consultas e Exames"},
        "TRANSPORTE": {"prefixo": "MT", "sala": 2, "nome": "Marcação de Transporte"},
    },
    "SENHA_FILA_PADRAO": "TRANSPORTE",
}

# --- Identidade institucional (branding) -------------------------------------
ORGAO = {
    "SISTEMA_NOME": "SIGTRANS Saúde",
    "SISTEMA_DESCRICAO": "Sistema de Gestão de Transporte de Pacientes",
    "PREFEITURA": "Prefeitura Municipal de Barão de Cocais – MG",
    "SECRETARIA": "Secretaria Municipal de Saúde",
    "DEPARTAMENTO": "Departamento de Informática e Tecnologia",
    "RESPONSAVEL": "Aristides Ferreira Junior",
    "RESPONSAVEL_TELEFONE": "(31) 3837-7661",
    "LOGO": "img/logo-prefeitura.jpg",  # brasão oficial da Prefeitura
}
