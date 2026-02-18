"""
Django settings for shiftedblog project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from django.utils.csp import CSP

    DJANGO_CSP_AVAILABLE = True
except ImportError:
    CSP = None
    DJANGO_CSP_AVAILABLE = False

load_dotenv()


def get_bool_env(key, default=False):
    """
    Convert environment variable to boolean.

    Handles string values: 'true', '1', 'yes', 'on' -> True
                          'false', '0', 'no', 'off', '' -> False
    If env var is not set, returns the default (boolean).
    """
    value = os.environ.get(key)
    if value is None:
        return default
    # Convert string to boolean
    return value.lower() in ("true", "1", "yes", "on")


def get_int_env(key, default=0):
    """Convert environment variable to integer."""
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


# Django settings

# DB settings
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT")


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable must be set. "
        "Use Doppler or set it in your environment."
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool_env("DEBUG", False)

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Site URL for sitemap and robots.txt (defaults to first ALLOWED_HOST with https://)
SITE_URL = os.environ.get("SITE_URL")
if not SITE_URL and ALLOWED_HOSTS:
    # Auto-detect from first allowed host (use https in production, http in dev)
    first_host = ALLOWED_HOSTS[0].strip()
    if first_host and first_host not in ("localhost", "127.0.0.1"):
        SITE_URL = f"https://{first_host}"
    else:
        SITE_URL = f"http://{first_host}"

SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",  # TOTP: Google Authenticator, Authy, etc.
    "django_otp.plugins.otp_static",  # Backup tokens
    "django_ratelimit",
    "two_factor",
    "taggit",
    "django_ckeditor_5",
    "core",
    "team",
    "editor",
]

_MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "axes.middleware.AxesMiddleware",
]
if DJANGO_CSP_AVAILABLE:
    _MIDDLEWARE.insert(1, "django.middleware.csp.ContentSecurityPolicyMiddleware")
    _MIDDLEWARE.insert(
        2, "shiftedblog.security_headers_middleware.PermissionsPolicyMiddleware"
    )
else:
    _MIDDLEWARE.insert(
        1, "shiftedblog.security_headers_middleware.SecurityHeadersMiddleware"
    )
MIDDLEWARE = _MIDDLEWARE

ROOT_URLCONF = "shiftedblog.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = "shiftedblog.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": db_host,
        "PORT": db_port,
        "NAME": db_name,
        "USER": db_user,
        "PASSWORD": db_pass,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache configuration (required for django-ratelimit)
# Using Redis cache backend for atomic increment support
# Redis is required for django-ratelimit to work properly with multiple workers
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "shiftedblog",
        "TIMEOUT": 300,  # Default timeout: 5 minutes
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,  # Enforce minimum 12 character passwords
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "core.User"
LOGIN_URL = "two_factor:login"

# Admin URL path (configurable for security through obscurity)
# Default to 'mellon' but can be changed via ADMIN_URL environment variable
ADMIN_URL = os.environ.get("ADMIN_URL", "mellon").strip(
    "/"
)  # Remove leading/trailing slashes
LOGIN_REDIRECT_URL = f"/{ADMIN_URL}/"

AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend first in AUTHENTICATION_BACKENDS list.
    "axes.backends.AxesStandaloneBackend",
    # Django ModelBackend is the default authentication backend.
    "django.contrib.auth.backends.ModelBackend",
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static_blog"),  # Project-level static files
]

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "media/"


# Security settings
# Determine if we're in production (not DEBUG mode)
IS_PRODUCTION = not DEBUG

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Session security - production-safe defaults
SESSION_COOKIE_SECURE = get_bool_env("SESSION_COOKIE_SECURE", IS_PRODUCTION)
SESSION_COOKIE_HTTPONLY = get_bool_env("SESSION_COOKIE_HTTPONLY", True)
SESSION_COOKIE_AGE = get_int_env("SESSION_COOKIE_AGE", 3600)  # 1 hour default
SESSION_EXPIRE_AT_BROWSER_CLOSE = get_bool_env("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
SESSION_COOKIE_SAMESITE = "Lax"  # Protection against CSRF attacks

# SSL/TLS settings
SECURE_SSL_REDIRECT = get_bool_env("SECURE_SSL_REDIRECT", IS_PRODUCTION)

# CSRF protection
CSRF_COOKIE_SECURE = get_bool_env("CSRF_COOKIE_SECURE", IS_PRODUCTION)
# CSRF_COOKIE_HTTPONLY need to be False for CKEditor
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
# Get CSRF trusted origins from environment, default to empty list in production
csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(",")]
    # Validate: In production, all CSRF trusted origins must use HTTPS
    if IS_PRODUCTION:
        http_origins = [
            origin for origin in CSRF_TRUSTED_ORIGINS if origin.startswith("http://")
        ]
        if http_origins:
            raise ValueError(
                f"Security Error: CSRF_TRUSTED_ORIGINS contains HTTP URLs in "
                f"production: {http_origins}. All origins must use HTTPS in "
                f"production. Current origins: {CSRF_TRUSTED_ORIGINS}"
            )
else:
    # Development defaults: allow HTTP for localhost only
    CSRF_TRUSTED_ORIGINS = (
        [] if IS_PRODUCTION else ["http://localhost:8000", "http://127.0.0.1:8000"]
    )

# HSTS (HTTP Strict Transport Security)
# Default: 1 year (31536000 seconds) in production, 0 in development
SECURE_HSTS_SECONDS = get_int_env(
    "SECURE_HSTS_SECONDS", 31536000 if IS_PRODUCTION else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = get_bool_env(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", IS_PRODUCTION
)
SECURE_HSTS_PRELOAD = get_bool_env("SECURE_HSTS_PRELOAD", IS_PRODUCTION)

# Security headers
SECURE_REFERRER_POLICY = os.environ.get(
    "SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin"
)
SECURE_BROWSER_XSS_FILTER = get_bool_env("SECURE_BROWSER_XSS_FILTER", True)
SECURE_CONTENT_TYPE_NOSNIFF = get_bool_env("SECURE_CONTENT_TYPE_NOSNIFF", True)

X_FRAME_OPTIONS = "DENY"

PREPEND_WWW = get_bool_env("PREPEND_WWW", False)

# Additional security headers (set via middleware or nginx)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Content-Security-Policy: Django 6 uses SECURE_CSP + ContentSecurityPolicyMiddleware;
# Django 5 uses CONTENT_SECURITY_POLICY string + SecurityHeadersMiddleware.
if DJANGO_CSP_AVAILABLE:
    assert CSP is not None  # narrow for type checker
    SECURE_CSP = {
        "default-src": [CSP.SELF],
        "script-src": [
            CSP.SELF,
            "'unsafe-inline'",
            "'unsafe-eval'",
            "https://cdn.jsdelivr.net",
            "https://kit.fontawesome.com",
        ],
        "style-src": [
            CSP.SELF,
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://ka-f.fontawesome.com",
        ],
        "img-src": [CSP.SELF, "data:", "https:"],
        "font-src": [
            CSP.SELF,
            "https://cdn.jsdelivr.net",
            "https://kit.fontawesome.com",
            "https://ka-f.fontawesome.com",
            "data:",
        ],
        "connect-src": [
            CSP.SELF,
            "https://kit.fontawesome.com",
            "https://ka-f.fontawesome.com",
        ],
        "frame-ancestors": [CSP.NONE],
        "base-uri": [CSP.SELF],
        "form-action": [CSP.SELF],
    }
else:
    CONTENT_SECURITY_POLICY = os.environ.get(
        "CONTENT_SECURITY_POLICY",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.jsdelivr.net https://kit.fontawesome.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
        "https://ka-f.fontawesome.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net https://kit.fontawesome.com "
        "https://ka-f.fontawesome.com data:; "
        "connect-src 'self' https://kit.fontawesome.com "
        "https://ka-f.fontawesome.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )

# Permissions-Policy (formerly Feature-Policy)
# Restrict access to browser features for enhanced privacy
PERMISSIONS_POLICY = os.environ.get(
    "PERMISSIONS_POLICY",
    "geolocation=(), "
    "microphone=(), "
    "camera=(), "
    "magnetometer=(), "
    "gyroscope=(), "
    "speaker=(), "
    "vibrate=(), "
    "fullscreen=(self), "
    "payment=()",
)

# CKEditor Settings
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": {
            "items": [
                "heading",
                "|",
                "Bold",
                "Italic",
                "Underline",
                "Strikethrough",
                "code",
                "Subscript",
                "Superscript",
                "specialCharacters",
                "highlight",
                "RemoveFormat",
                "|",
                "NumberedList",
                "BulletedList",
                "todoList",
                "|",
                "Blockquote",
                "|",
                "codeBlock",
                "|",
                "alignment",
                "Outdent",
                "Indent",
                "|",
                "insertImage",
                "|",
                "Link",
                "Unlink",
                "|",
                "fontSize",
                "fontFamily",
                "fontColor",
                "fontBackgroundColor",
                "|",
                "mediaEmbed",
                "insertTable",
                "HorizontalLine",
                "sourceEditing",
                "|",
                "undo",
                "redo",
            ],
            "shouldNotGroupWhenFull": True,
        },
        "image": {
            "toolbar": [
                "imageStyle:full",
                "imageStyle:side",
                "imageStyle:alignLeft",
                "imageStyle:alignCenter",
                "imageStyle:alignRight",
                "toggleImageCaption",
                "imageTextAlternative",
            ],
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ],
        },
        # Inter as first (and default) choice
        "fontFamily": {
            "options": [
                "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
                "default",
                "Arial, Helvetica, sans-serif",
                "Georgia, serif",
                "Times New Roman, Times, serif",
                "Verdana, Geneva, sans-serif",
            ],
        },
        "fontSize": {
            "options": [
                {"title": "Body", "model": "18px"},
                "default",
                "tiny",
                "small",
                "big",
                "huge",
            ],
        },
    },
}

# Define a constant in settings.py to specify file upload permissions
CKEDITOR_5_FILE_UPLOAD_PERMISSION = (
    "staff"  # Possible values: "staff", "authenticated", "any"
)
CK_EDITOR_5_UPLOAD_FILE_VIEW_NAME = "custom_image_upload"


# Dzen verification file (optional) - returns string or None
DZEN_VERIFICATION_FILE = os.environ.get("DZEN_VERIFICATION_FILE") or None

# django-ratelimit configuration for application-level rate limiting
# Works alongside nginx rate limiting for defense in depth
# Uses default cache backend (database cache or memory cache)
RATELIMIT_ENABLE = get_bool_env("RATELIMIT_ENABLE", IS_PRODUCTION)
RATELIMIT_USE_CACHE = "default"  # Use Django's default cache backend

# django-axes configuration for brute force protection
AXES_ENABLED = get_bool_env("AXES_ENABLED", True)
AXES_FAILURE_LIMIT = get_int_env(
    "AXES_FAILURE_LIMIT", 5
)  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = get_int_env("AXES_COOLOFF_TIME", 1)  # 1 hour lockout
# AXES_LOCKOUT_CALLABLE: Use default database lockout (None = default behavior)
AXES_RESET_ON_SUCCESS = get_bool_env("AXES_RESET_ON_SUCCESS", True)
AXES_VERBOSE = get_bool_env("AXES_VERBOSE", True)
AXES_LOGIN_FAILURE_LIMIT = get_int_env("AXES_LOGIN_FAILURE_LIMIT", 5)
# Lockout by both IP address and username (replaces deprecated AXES_ONLY_USER_FAILURES)
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_LOCKOUT_TEMPLATE = (
    "two_factor/lockout.html"  # Optional: create custom lockout template
)
AXES_LOCKOUT_URL = None  # Use default lockout view

# Logging configuration for security events
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "security": {
            "format": "{levelname} {asctime} [{module}] {message}",
            "style": "{",
        },
        "security_detailed": {
            "format": "{levelname} {asctime} [{module}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "security.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "security",
        },
        "auth_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "authentication.log"),
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "security_detailed",
        },
    },
    "loggers": {
        # Django security events (CSRF, XSS, etc.)
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        # django-axes: Failed login attempts, lockouts
        "axes": {
            "handlers": ["console", "security_file", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
        # django-ratelimit: Rate limiting events
        "django_ratelimit": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        # Two-factor authentication events
        "django_otp": {
            "handlers": ["console", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
        "two_factor": {
            "handlers": ["console", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Authentication events (login, logout, etc.)
        "django.contrib.auth": {
            "handlers": ["console", "auth_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Request errors (4xx, 5xx)
        "django.request": {
            "handlers": ["console", "security_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Server errors
        "django.server": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# Ensure logs directory exists
logs_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(logs_dir, exist_ok=True)
