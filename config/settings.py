"""
Django settings for NutriSync — Plataforma de Gestión Profesional para Nutricionistas.
"""

from pathlib import Path
from decouple import config

# Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent


# Seguridad

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-+cf^9q!ws)x$@j*a5d0w@j@f(7l9o^dvuoh7b-+)jieg_!c+8d",
)

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0",
    cast=lambda v: [s.strip() for s in v.split(",")],
)
if DEBUG:
    ALLOWED_HOSTS.append("*")

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000",
    cast=lambda v: [s.strip() for s in v.split(",")]
)


# Aplicaciones

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",  # Cabeceras CORS para la comunicación con la app móvil
    # Aplicaciones del proyecto
    "core.apps.CoreConfig",  # Auth, dashboard, perfil del nutricionista (CoreConfig para signals)
    "pacientes",  # Gestión de pacientes
    "agendas.apps.AgendasConfig",  # Agenda de citas
    "nutricion",  # Base de alimentos y planes nutricionales
    "seguimiento",  # Medidas corporales y notas clínicas
    "reportes",  # Reportes clínicos, operativos y financieros
    "facturacion",  # Facturación, cobros y suscripciones
    "administracion",  # Panel de Administración Global (BackOffice SaaS)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS Middleware (debe ir antes de CommonMiddleware)
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.ThreadLocalRequestMiddleware",  # Permite acceder al request/usuario actual de forma global en modelos y formularios (ThreadLocal)
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
                # Añade el perfil a las plantillas.
                "core.context_processors.perfil_nutricionista",
                # Añade el perfil del administrador.
                "administracion.context_processors.admin_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Autenticación

# Redirección de usuarios no autenticados
LOGIN_URL = "/login/"
# Tras un login exitoso, va al dashboard
LOGIN_REDIRECT_URL = "/"
# Tras logout, vuelve al login
LOGOUT_REDIRECT_URL = "/login/"


# Base de datos

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="nutrisync_db"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        # DB_HOST=db con Docker; DB_HOST=localhost sin Docker
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
    }
}


# Contraseñas

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Idioma y zona horaria

# Mensajes en español
LANGUAGE_CODE = "es"

TIME_ZONE = "America/Lima"

USE_I18N = True
USE_TZ = True


# Archivos estáticos

STATIC_URL = "/static/"

# Estilos del proyecto
STATICFILES_DIRS = [BASE_DIR / "static"]

# Destino de collectstatic
STATIC_ROOT = BASE_DIR / "staticfiles"


# Archivos subidos

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS para la aplicación móvil
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:8081,http://127.0.0.1:8081",
        cast=lambda v: [s.strip() for s in v.split(",")]
    )


# Stripe
STRIPE_PUBLIC_KEY     = config("STRIPE_PUBLIC_KEY",     default="pk_test_placeholder")
STRIPE_SECRET_KEY     = config("STRIPE_SECRET_KEY",     default="sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="whsec_placeholder")
STRIPE_CURRENCY = "PEN"
PAYMENT_SANDBOX = config("PAYMENT_SANDBOX", default=DEBUG, cast=bool)
TRUST_X_FORWARDED_FOR = config(
    "TRUST_X_FORWARDED_FOR", default=False, cast=bool
)


# Clave de registro administrativo
ADMIN_REGISTER_KEY = config("ADMIN_REGISTER_KEY", default="nutrisync-admin-2025")
