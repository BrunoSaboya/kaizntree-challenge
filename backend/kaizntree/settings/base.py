import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = False

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.users",
    "apps.inventory",
    "apps.orders",
    "apps.financials",
    "apps.suppliers",
    "apps.forecasting",
    "apps.ai_workflows",
    "apps.integrations",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kaizntree.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "kaizntree.wsgi.application"

import dj_database_url as _dj_db_url

if "DATABASE_URL" not in os.environ:
    _default_db_url = (
        f"postgresql://{os.environ['POSTGRES_USER']}"
        f":{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
        f":{os.environ.get('POSTGRES_PORT', '5432')}"
        f"/{os.environ.get('POSTGRES_DB', 'kaizntree')}"
    )
else:
    _default_db_url = None

DATABASES = {
    "default": _dj_db_url.config(
        default=_default_db_url,
        conn_max_age=600,
        ssl_require=False,
    )
}

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = ["apps.users.backends.OrgAwareBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "ai_workflow": "10/min",
    },
}

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# E-commerce integrations (optional — leave blank to disable)
SHOPIFY_WEBHOOK_SECRET = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN", "")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

AMAZON_SELLER_ID = os.environ.get("AMAZON_SELLER_ID", "")
AMAZON_LWA_CLIENT_ID = os.environ.get("AMAZON_LWA_CLIENT_ID", "")
AMAZON_LWA_CLIENT_SECRET = os.environ.get("AMAZON_LWA_CLIENT_SECRET", "")
AMAZON_LWA_REFRESH_TOKEN = os.environ.get("AMAZON_LWA_REFRESH_TOKEN", "")
AMAZON_AWS_ACCESS_KEY = os.environ.get("AMAZON_AWS_ACCESS_KEY", "")
AMAZON_AWS_SECRET_KEY = os.environ.get("AMAZON_AWS_SECRET_KEY", "")
AMAZON_MARKETPLACE_ID = os.environ.get("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER")

# ERP integrations (optional — leave blank to disable)
QUICKBOOKS_CLIENT_ID = os.environ.get("QUICKBOOKS_CLIENT_ID", "")
QUICKBOOKS_CLIENT_SECRET = os.environ.get("QUICKBOOKS_CLIENT_SECRET", "")
QUICKBOOKS_REALM_ID = os.environ.get("QUICKBOOKS_REALM_ID", "")
QUICKBOOKS_ACCESS_TOKEN = os.environ.get("QUICKBOOKS_ACCESS_TOKEN", "")
QUICKBOOKS_REFRESH_TOKEN = os.environ.get("QUICKBOOKS_REFRESH_TOKEN", "")
QUICKBOOKS_ENVIRONMENT = os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")

NETSUITE_ACCOUNT_ID = os.environ.get("NETSUITE_ACCOUNT_ID", "")
NETSUITE_CONSUMER_KEY = os.environ.get("NETSUITE_CONSUMER_KEY", "")
NETSUITE_CONSUMER_SECRET = os.environ.get("NETSUITE_CONSUMER_SECRET", "")
NETSUITE_TOKEN_ID = os.environ.get("NETSUITE_TOKEN_ID", "")
NETSUITE_TOKEN_SECRET = os.environ.get("NETSUITE_TOKEN_SECRET", "")
NETSUITE_SUBSIDIARY_ID = os.environ.get("NETSUITE_SUBSIDIARY_ID", "1")

_access_lifetime_minutes = int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
_refresh_lifetime_days = int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=_access_lifetime_minutes),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=_refresh_lifetime_days),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_COOKIE": "refresh_token",
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",
    "AUTH_COOKIE_SECURE": False,  # set True in production
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Kaizntree Inventory API",
    "DESCRIPTION": "Inventory management system for F&B CPG brands",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost"
).split(",")
CORS_ALLOW_CREDENTIALS = True
