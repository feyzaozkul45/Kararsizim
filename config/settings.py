"""
Django settings for the Kararsizim project.

Secrets and environment-specific values are read from the environment
(a local `.env` file is loaded via python-dotenv).
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_list(name, default=""):
    """Read a comma separated environment variable as a list."""
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --- Core -------------------------------------------------------------------

DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "insecure-dev-only-key"
    else:
        raise RuntimeError("SECRET_KEY environment variable is required when DEBUG is False.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")


# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "polls",
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
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database ---------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0)}
    # Supabase pooler (PgBouncer, transaction mode) requirements.
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"
    # psycopg 3 prepares statements by default, which PgBouncer's transaction mode can't handle.
    DATABASES["default"]["OPTIONS"]["prepare_threshold"] = None
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# --- Auth -------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internationalization ---------------------------------------------------

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True


# --- Static files -----------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Serve files straight from `static/` so no collectstatic build step is needed.
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Production security ----------------------------------------------------

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# --- Authentication flow ----------------------------------------------------

AUTHENTICATION_BACKENDS = ["accounts.backends.EmailOrUsernameBackend"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "poll_list"
LOGOUT_REDIRECT_URL = "poll_list"
