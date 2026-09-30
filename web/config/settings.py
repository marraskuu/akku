import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "akku.hiekkalaatikko.pro,localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "https://akku.hiekkalaatikko.pro",
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "telemetry",
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
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

_db_url = urlsplit(os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL") or "")


def _db_setting(*names, url_value, default):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return url_value or default


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": _db_setting(
            "MYSQLDATABASE", "MYSQL_DATABASE", url_value=_db_url.path.lstrip("/"), default="railway"
        ),
        "USER": _db_setting("MYSQLUSER", "MYSQL_USER", url_value=unquote(_db_url.username or ""), default="root"),
        "PASSWORD": _db_setting(
            "MYSQLPASSWORD", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD",
            url_value=unquote(_db_url.password or ""), default="",
        ),
        "HOST": _db_setting("MYSQLHOST", "MYSQL_HOST", url_value=_db_url.hostname, default="127.0.0.1"),
        "PORT": _db_setting("MYSQLPORT", "MYSQL_PORT", url_value=_db_url.port and str(_db_url.port), default="3306"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedStaticFilesStorage"
    },
}
WHITENOISE_USE_FINDERS = DEBUG

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "devices"
LOGOUT_REDIRECT_URL = "login"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_000_000

INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
