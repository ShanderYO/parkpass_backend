"""
Django settings for parkpass project.

Generated by 'django-admin startproject' using Django 1.8.9.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'vpqbqbi3@8t4wig82x6fj4_a2o$9zf=_bzh(^d2-n0xdqi#c%s'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

SMS_GATEWAY_API_KEY = "6831k8gxzptd8unfb5fk58rg7sutsjbybrb8faao"
SMS_SENDER_NAME = "PARKPASS"

TINKOFF_TERMINAL_KEY = "1516954410942DEMO"
TINKOFF_TERMINAL_PASSWORD = "dybcdp86npi8s9fv"

# Application definition

INSTALLED_APPS = (
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'autotask',
    'base',
    'accounts',
    'payments',
    'parkings',
    'rps_vendor',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'base.middleware.TokenAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'parkpass.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'admin_tools.template_loaders.Loader',
            ]
        },

    },
]

WSGI_APPLICATION = 'parkpass.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
DATABASES = {}

if os.environ.get("PROD"):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get("POSTGRES_DB_NAME"),
            'USER': os.environ.get("POSTGRES_USER"),
            'PASSWORD': os.environ.get("POSTGRES_PASSWORD"),
            'HOST': os.environ.get("POSTGRES_DATABASE_HOST"), # Set to empty string for localhost.
            'PORT': '', # Set to empty string for default.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Email configs
# TODO change SMTP parameters
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'noreply@parkpass.ru'
EMAIL_HOST_PASSWORD = 'noreplyParol'
EMAIL_USE_TLS = True

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

BASE_LOGGER_NAME = "parkpass"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s.%(module)s.%(funcName)s:%(lineno)s -> %(message)s'
        },
        'notime': {
            'format': '%(levelname)s %(name)s.%(module)s.%(funcName)s:%(lineno)s -> %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'parkpass.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter':'notime'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'parkpass': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        }
    }
}

AUTOTASK_IS_ACTIVE = True
AUTOTASK_WORKER_MONITOR_INTERVALL = 60
AUTOTASK_HANDLE_TASK_IDLE_TIME = 10


STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = '/api/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = '/media/'