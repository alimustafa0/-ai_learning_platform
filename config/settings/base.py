from pathlib import Path
from decouple import config
from django.urls import reverse_lazy
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# Application definition
INSTALLED_APPS = [
    'users',
    'courses',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_ckeditor_5',
    'django_ratelimit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "courses.context_processors.user_level",
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
import sys

# Check if we're running tests
TESTING = 'test' in sys.argv

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# If we're in production and have DATABASE_URL set, use PostgreSQL
if config('ENVIRONMENT') == 'production' and config('DATABASE_URL', default=None):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,  # Keep connections alive for 600 seconds (10 minutes)
        conn_health_checks=True,  # Check if connection is still alive
    )

# Database Optimizations
if not TESTING:
    # Add persistent connections for better performance
    DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes

    # Ensure we're using UTF-8 for SQLite (supports emoji!)
    if 'sqlite3' in DATABASES['default']['ENGINE']:
        from django.db.backends.signals import connection_created
        def activate_foreign_keys(sender, connection, **kwargs):
            """Enable foreign key constraints and UTF-8 support for SQLite"""
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                cursor.execute('PRAGMA foreign_keys = ON;')
                cursor.execute('PRAGMA encoding = "UTF-8";')
        connection_created.connect(activate_foreign_keys)

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Ensure the media directory exists
os.makedirs(MEDIA_ROOT, exist_ok=True)

# Custom user model
AUTH_USER_MODEL = "users.User"

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'formatter': 'verbose',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'courses': {  # Your app-specific logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'users': {  # Your other app
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Authentication URLs
LOGIN_REDIRECT_URL = reverse_lazy('dashboard')
LOGOUT_REDIRECT_URL = reverse_lazy('welcome')

# CKEditor Configuration
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ],
        'height': 300,
        'width': '100%',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379'),
    }
}

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                   'bulletedList', 'numberedList', 'blockQuote', '|',
                   'undo', 'redo', '|',
                   'insertTable', 'tableColumn', 'tableRow', 'mergeTableCells'],
        'height': '300px',
        'width': '100%',
    },
}


# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
SITE_URL = config("SITE_URL", default="http://localhost:8000")
