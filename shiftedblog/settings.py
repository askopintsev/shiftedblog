"""
Django settings for shiftedblog project.

Generated by 'django-admin startproject' using Django 3.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

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
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG")

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',

    'axes',
    'django_otp',
    'django_otp.plugins.otp_totp',  # TOTP: Google Authenticator, Authy, etc.
    'django_otp.plugins.otp_static',  # Backup tokens
    'two_factor',
    'taggit',
    'sslserver',
    'django_ckeditor_5',

    'blog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    # AxesMiddleware should be the last middleware in the MIDDLEWARE list.
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'shiftedblog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'blog_tags': 'templates.blog.templatetags.blog_tags',
            }
        },
    },
]

WSGI_APPLICATION = 'shiftedblog.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': db_host,
        'PORT': db_port,
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_pass,
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'blog.User'
LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = '/mellon'

AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend should be the first backend in the AUTHENTICATION_BACKENDS list.
    'axes.backends.AxesStandaloneBackend',

    # Django ModelBackend is the default authentication backend.
    'django.contrib.auth.backends.ModelBackend',
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # Project-level static files
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


# Security settings
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', False)
SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', False)
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.environ.get('SESSION_EXPIRE_AT_BROWSER_CLOSE', False)

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', False)

CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', False)
### CSRF_COOKIE_HTTPONLY need to be False for CKEditor
CSRF_COOKIE_HTTPONLY = False

SECURE_HSTS_SECONDS = os.environ.get('SECURE_HSTS_SECONDS', 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', False)

SECURE_REFERRER_POLICY = os.environ.get('SECURE_BROWSER_XSS_FILTER','no-referrer-when-downgrade')
SECURE_BROWSER_XSS_FILTER = os.environ.get('SECURE_BROWSER_XSS_FILTER', False)
SECURE_CONTENT_TYPE_NOSNIFF = os.environ.get('SECURE_CONTENT_TYPE_NOSNIFF', False)

X_FRAME_OPTIONS = 'DENY'

# CKEditor Settings
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|',
                'Bold', 'Italic', 'Underline', 'Strikethrough', 'code', 'Subscript', 
                'Superscript',  'specialCharacters', 'highlight', 'RemoveFormat', '|',
                'NumberedList', 'BulletedList', 'todoList', '|',
                'Blockquote', '|',
                'codeBlock', '|',
                'alignment', 'Outdent', 'Indent', '|',
                'insertImage', '|',
                'Link', 'Unlink', '|',
                'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
                'mediaEmbed',
                'insertTable',
                'HorizontalLine',
                'sourceEditing', '|',
                'undo', 'redo',
            ],
            "shouldNotGroupWhenFull": True,
        },
        'image': {
            'toolbar': [
                'imageStyle:full', 'imageStyle:side', 'imageStyle:alignLeft',
                'imageStyle:alignCenter', 'imageStyle:alignRight', 'toggleImageCaption',
                'imageTextAlternative',
            ],
        },
        'table': {
            'contentToolbar': [
                'tableColumn', 'tableRow', 'mergeTableCells',
                'tableProperties', 'tableCellProperties',
            ],
        },
    },
}

# Define a constant in settings.py to specify file upload permissions
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"  # Possible values: "staff", "authenticated", "any"
CK_EDITOR_5_UPLOAD_FILE_VIEW_NAME = "custom_image_upload"


DZEN_VERIFICATION_FILE = os.environ.get('DZEN_VERIFICATION_FILE', False)