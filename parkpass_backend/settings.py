"""
Django settings for parkpass_backend project.

Generated by 'django-admin startproject' using Django 2.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'kickk&tua$aj_jq4(+kt5wb4jfgqp5#t-ki-dh1nk2zs54al0l'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.environ.get("DJANGO_DEBUG", 1)) == 1

ALLOWED_HOSTS = [".parkpass.ru", "127.0.0.1"]

SMS_GATEWAY_ENABLED = int(os.environ.get("SMS_GATEWAY_ENABLE", 1)) == 1

SMS_GATEWAYS = [{
    "provider": "sms_gateway.providers.SMSProviderUnisender",
    "sender_name": "PARKPASS",
    "credentials": {
        "api_key": "6831k8gxzptd8unfb5fk58rg7sutsjbybrb8faao"
    },
    "is_default": False
},
{
    "provider": "sms_gateway.providers.SMSProviderBeeline",
    "sender_name": "PARKPASS",
    "credentials": {
        "user": 1659361,
        "password": 9661673802
    },
    "is_default": True
}]

TINKOFF_DEFAULT_TERMINAL_KEY = "1516954410942DEMO"
TINKOFF_DEFAULT_TERMINAL_PASSWORD = "dybcdp86npi8s9fv"

TINKOFF_TERMINAL_KEY = TINKOFF_DEFAULT_TERMINAL_KEY
TINKOFF_TERMINAL_PASSWORD = TINKOFF_DEFAULT_TERMINAL_PASSWORD

# Application definition
#TINKOFF_API_REFRESH_TOKEN = 't.MQCiorv_cccpkAw5u5kknrpNd54WbunlOx4iy6cCEH69BbwSDQQWql2nnTuHxY_VpuHtrPW8dHUojjwOl3uc5A'
PARKPASS_INN = "7725415044"


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #'admin_tools',
    #'admin_tools.theming',
    #'admin_tools.menu',
    #admin_tools.dashboard',

    'django_celery_beat',
    #'tests',
    'base',
    'accounts',
    'vendors',
    'payments',
    'parkings',
    'jwtauth',
    'rps_vendor',
    'owners',
    'control',
    'partners'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'base.middleware.ComplexAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

ROOT_URLCONF = 'parkpass_backend.urls'

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
            ]
        },

    },
]

WSGI_APPLICATION = 'parkpass_backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {}

if not os.environ.get("DEV"):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get("POSTGRES_DB_NAME", "parkpass"),
            'USER': os.environ.get("POSTGRES_USER", "parkpass"),
            'PASSWORD': os.environ.get("POSTGRES_PASSWORD", "parkpass"),
            'HOST': os.environ.get("POSTGRES_DATABASE_HOST", "185.158.155.26"),  # 185.158.155.120 Set to empty string for localhost.
            'PORT': '', # Set to empty string for default.
        }
    }
elif os.environ.get("PROD"):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get("POSTGRES_DB_NAME", ""),
            'USER': os.environ.get("POSTGRES_USER", ""),
            'PASSWORD': os.environ.get("POSTGRES_PASSWORD", ""),
            'HOST': os.environ.get("POSTGRES_DATABASE_HOST", ""),  # Set to empty string for localhost.
            'PORT': '',  # Set to empty string for default.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Email configs
# TODO change SMTP parameters
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'noreply@parkpass.ru'
EMAIL_HOST_PASSWORD = 'noreplyParol'
EMAIL_USE_TLS = True


BASE_LOGGER_NAME = "parkpass"
LOG_DIR = 'media/logs'
LOG_FILE = os.path.join(LOG_DIR, 'parkpass.log')
REQUESTS_LOG_FILE = os.path.join(LOG_DIR, 'requests.log')
REQUESTS_LOGGER_NAME = 'requests'

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
        'requests': {
            'format': '%(asctime)s: %(message)s'
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
            'filename': LOG_FILE,
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'requests_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': REQUESTS_LOG_FILE,
            'when': 'D',
            'backupCount': 7,
            'formatter': 'requests'
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
            'propagate': True
        },
        BASE_LOGGER_NAME: {
            'handlers': ['file'],
            'level': 'DEBUG'
        },
        REQUESTS_LOGGER_NAME: {
            'handlers': ['requests_file'],
            'level': 'DEBUG'
        }
    }
}


# REDIS related settings
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")

BROKER_URL = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_RESULT_BACKEND = 'redis://' + REDIS_HOST + ':' + REDIS_PORT + '/0'

# Other Celery settings
CELERY_BEAT_SCHEDULE = {
    'task-accounts-order': {
        'task': 'accounts.tasks.generate_orders_and_pay',
        'schedule': 30.0
    },
    'task-rps-ask-update': {
        'task': 'rps_vendor.tasks.request_rps_session_update',
        'schedule': 30.0
    },
    'task-check-prolong-subscription': {
        'task': 'rps_vendor.tasks.prolong_subscription_sheduler',
        'schedule': 60 * 60 * 12 # two times per day
    },
    'task-notify-mos-parking-vendor': {
        'task': 'vendor.task.notify_mos_parking',
        'schedule': 15.0
    }
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = '/api/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = '/api/media/'
AVATARS_URL = MEDIA_URL + 'avatars/'
AVATARS_ROOT = os.path.join(BASE_DIR, "media/avatars")
REPORTS_ROOT = os.path.join(BASE_DIR, "media/reports")
DEFAULT_AVATAR_URL = MEDIA_URL + 'default.jpg'


PAGINATION_OBJECTS_PER_PAGE = 10

ZENDESK_WIDGET_SECRET = 'fecb58d1e0ab86c5b92360141a0acbc3'
ZENDESK_CHAT_SECRET = '4A584DAA027F945513204BE0B22DEE5C97B08925A7CFA47CBA027609FA81F555'
#ZENDESK_MOBILE_SECRET = 'neWp8PhWWrQDtFHVbMFjGRM3iEk5GkwagB9omF784bWSruwO'
ZENDESK_MOBILE_SECRET = "SQ4rB6IylfXtSH5p5yiNS2XGgJOXlOOIR8ZjieGcUMXI8sed"

# Settings auth
SECRET_KEY_JWT = os.environ.get("SECRET_KEY_JWT", 'secret')

ACCESS_TOKEN_LIFETIME_IN_SECONDS = 1* 60 * 60 # 1 hour
REFRESH_TOKEN_LIFETIME_IN_SECONDS = 60 * 60 * 24 * 14 # 2 weak
SECRET_TOKEN_LIFETIME_IN_MINUTE = 60 # 1 hour
