import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'vpqbqbi3@8t4wig82x6fj4_a2o$9zf=_bzh(^d2-n0xdqi#c%s'
DEBUG = int(os.environ.get("DJANGO_DEBUG", 1)) == 1
ALLOWED_HOSTS = ["parkpass.ru"]


SMS_GATEWAY_API_KEY = "6831k8gxzptd8unfb5fk58rg7sutsjbybrb8faao"
SMS_SENDER_NAME = "PARKPASS"
SMS_GATEWAY_ENABLED = int(os.environ.get("SMS_GATEWAY_ENABLE", 1)) == 1

TINKOFF_DEFAULT_TERMINAL_KEY = "1516954410942DEMO"
TINKOFF_DEFAULT_TERMINAL_PASSWORD = "dybcdp86npi8s9fv"
TINKOFF_TERMINAL_KEY = TINKOFF_DEFAULT_TERMINAL_KEY
TINKOFF_TERMINAL_PASSWORD = TINKOFF_DEFAULT_TERMINAL_PASSWORD


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
    'vendors',
    'payments',
    'parkings',
    'rps_vendor',
    'owners',
    'control'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'base.middleware.TokenAuthenticationMiddleware',
    # 'base.middleware.LoggingMiddleware',
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

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
            'propagate': True,
        },
        BASE_LOGGER_NAME: {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        REQUESTS_LOGGER_NAME: {
            'handlers': ['requests_file'],
            'level': 'DEBUG'
        }
    }
}

#CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
#CELERY_RESULT_BACKEND = 'django-db'

#CELERY_BEAT_SCHEDULE = {
#    'token-expiration-checker': {
#       'task': 'app.tasks.token_expiration_checker',
#        'schedule': 60.0, # every minute
#    }
#}

AUTOTASK_IS_ACTIVE = False
AUTOTASK_WORKER_MONITOR_INTERVALL = 60
AUTOTASK_HANDLE_TASK_IDLE_TIME = 10

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
DEFAULT_AVATAR_URL = MEDIA_URL + 'default.jpg'

PAGINATION_OBJECTS_PER_PAGE = 10

ZENDESK_SECRET = '7B0C54A93B4E01FC8B7AF3AE6ECFE0A010DFF763B118E745A60CF2D4480B360A'



