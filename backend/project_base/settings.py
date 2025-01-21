"""
Django settings for project_base project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os


def load_env_file():
    with open("../.env", "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=")
            os.environ[key] = value


load_env_file()


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-%q9_x-^4%d128ss#4xp&*hzg%%7&gru*=mg@qzb=w)$40_5lae"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]  # TODO: change this as soons as fixed IP is used to IPv4 and v6 of server


# Application definition

INSTALLED_APPS = [
    "data_map_backend.apps.DataMapBackendConfig",
    "legacy_backend.apps.LegacyBackendConfig",
    "columns.apps.ColumnsConfig",
    "ingest.apps.IngestConfig",
    "map.apps.MapConfig",
    "search.apps.SearchConfig",
    "workflows.apps.WorkflowsConfig",
    "filter.apps.FilterConfig",
    "write.apps.WriteConfig",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djangoql",
    "simple_history",
    "django_extensions",
    "django_filters",
    "rest_framework",
    "oauth2_provider",
    "corsheaders",
    "social_django",
    "drf_social_oauth2",
    "django_object_actions",
    "import_export",
    "django_prometheus",
    "django_svelte_jsoneditor",
]

MIDDLEWARE = [
    #'kolo.middleware.KoloMiddleware',
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    "project_base.middleware.Remove204ResponseContentMiddleware",
]

ROOT_URLCONF = "project_base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "project_base.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # },
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        "NAME": "visdatamap",
        "USER": "postgres",
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("postgres_host", "localhost"),
        "PORT": 5432,
    },
    # 'default': {
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': 'visdatamap',
    #     'USER': 'postgres',
    #     'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
    #     'HOST': 'staging.absclust.com',
    #     'PORT': 22851,
    # }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = "static_root/"  # should be changed to where the static files will be actually hosted

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 5000000000  # 5 GB max upload of e.g. map data

# Rest Framework

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "drf_social_oauth2.authentication.SocialAuthentication",
    ),
}

# DRF Social OAuth2
AUTHENTICATION_BACKENDS = (
    "oauth2_provider.backends.OAuth2Backend",
    "social_core.backends.google.GoogleOAuth2",
    "drf_social_oauth2.backends.DjangoOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

DRFSO2_PROPRIETARY_BACKEND_NAME = "VisualDataMapBackend"
# DRFSO2_URL_NAMESPACE = ?  # namespace for reversing URLs
# ACTIVATE_JWT = ?  # If set to True the access and refresh tokens will be JWTed. Default is False.

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "181787399123-6i9msa4oqik73gir0ei6g6lhp5jtgcau.apps.googleusercontent.com"  # client id
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "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"  # client secret

LOGIN_URL = "login"
LOGOUT_URL = "logout"
LOGIN_REDIRECT_URL = "home"

CORS_ORIGIN_ALLOW_ALL = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:55140",
    "http://home-server:55140",
    "http://localhost:55440",
    "http://home-server:55440",
    "http://localhost:55441",
    "http://home-server:55441",
    "http://luminosus-server-new.dynv6.net:55140",
    "http://luminosus-server-new.dynv6.net:55441",
    "http://www.luminosus.org:55440",
    "http://www.luminosus.org:55140",
    "https://bondiq.absclust.com",
    "https://v2.absclust.com",
    "https://feldberg.absclust.com",
    "https://bondiq.quiddityai.com",
    "https://v2.quiddityai.com",
    "https://feldberg.quiddityai.com",
    "https://bondiq.quiddity-ai.com",
    "https://v2.quiddity-ai.com",
    "https://feldberg.quiddity-ai.com",
    "https://tenders.absclust.com",
    "https://tenders.quiddityai.com",
    "https://tenders.enda.eu",
]


JAZZMIN_SETTINGS = {
    # Hide these models when generating side menu (e.g auth.user)
    "hide_models": ["data_map_backend.datasetspecificsettingsofcollection"],
    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)
    "order_with_respect_to": [
        "auth",
        "auth.user",
        "auth.group",
        "data_map_backend",
        "data_map_backend.organization",
        "data_map_backend.datasetschema",
        "data_map_backend.datasetfield",
        "data_map_backend.dataset",
        "data_map_backend.generator",
        "data_map_backend.embeddingspace",
        "data_map_backend.searchhistoryitem",
        "data_map_backend.storedmap",
        "data_map_backend.datacollection",
        "data_map_backend.collectionitem",
        "data_map_backend.collectioncolumn",
        "data_map_backend.trainedclassifier",
        "data_map_backend.chat",
        "data_map_backend.writingtask",
        "data_map_backend.serviceusage",
        "data_map_backend.importconverter",
        "data_map_backend.exportconverter",
        "data_map_backend.generationtask",
    ],
    # Custom icons for side menu apps/models See https://fontawesome.com/icons?d=gallery&m=free&v=5.0.0,5.0.1,5.0.10,5.0.11,5.0.12,5.0.13,5.0.2,5.0.3,5.0.4,5.0.5,5.0.6,5.0.7,5.0.8,5.0.9,5.1.0,5.1.1,5.2.0,5.3.0,5.3.1,5.4.0,5.4.1,5.4.2,5.13.0,5.12.0,5.11.2,5.11.1,5.10.0,5.9.0,5.8.2,5.8.1,5.7.2,5.7.1,5.7.0,5.6.3,5.5.0,5.4.2
    # for the full list of 5.13.0 free icon classes
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
        "data_map_backend.organization": "fas fa-building",
        "data_map_backend.datasetschema": "fas fa-database",
        "data_map_backend.datasetfield": "fas fa-grip-lines",
        "data_map_backend.dataset": "fas fa-database",
        "data_map_backend.generationtask": "fas fa-tasks",
        "data_map_backend.generator": "fas fa-microchip",
        "data_map_backend.embeddingspace": "fas fa-globe",
        "data_map_backend.searchhistoryitem": "fas fa-clock",
        "data_map_backend.storedmap": "fas fa-map",
        "data_map_backend.datacollection": "fas fa-list",
        "data_map_backend.collectionitem": "fas fa-file",
        "data_map_backend.collectioncolumn": "fas fa-columns",
        "data_map_backend.trainedclassifier": "fas fa-filter",
        "data_map_backend.chat": "fas fa-comments",
        "data_map_backend.writingtask": "fas fa-edit",
        "data_map_backend.serviceusage": "fas fa-chart-line",
        "data_map_backend.importconverter": "fas fa-file-import",
        "data_map_backend.exportconverter": "fas fa-file-export",
        "data_map_backend.user": "fas fa-user",
    },
    "show_ui_builder": True,
    "site_logo": "icon.png",
    "topmenu_links": [
        # Url that gets reversed (Permissions can be added)
        {"name": "Map / Classification Workspace →", "url": "/"},
    ],
}

# configure Django logging to exclude /org/data_map/health from logging:
# see https://stackoverflow.com/a/41620949


def skip_health_requests(record):
    if not record.args:
        return True
    paths_excluded_from_logging = [
        "/org/data_map/health",
        "/metrics",
    ]
    for path in paths_excluded_from_logging:
        if path in str(record.args[0]):
            return False
    return True


def skip_some_legacy_backend_routes(record):
    if not record.args:
        return True
    # return False if it should be ignored
    paths_excluded_from_logging = [
        "/data_backend/map/result",
        "/data_backend/document/details_by_id",
        "/data_backend/upload_files/status",
        "/data_backend/health",
        "/data_backend/db_health",
        "/legacy_backend/map/result",
        "/legacy_backend/document/details_by_id",
        "/legacy_backend/upload_files/status",
        "/legacy_backend/health",
        "/legacy_backend/db_health",
    ]
    for path in paths_excluded_from_logging:
        if path in str(record.args[0]):
            return False
    return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "exclude_health": {"()": "django.utils.log.CallbackFilter", "callback": skip_health_requests},
        "exclude_some_legacy_backend_routes": {
            "()": "django.utils.log.CallbackFilter",
            "callback": skip_some_legacy_backend_routes,
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["exclude_health", "exclude_some_legacy_backend_routes"],
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

# Django Prometheus / Grafana
PROMETHEUS_METRIC_NAMESPACE = "absclust_v2"

AUTH_USER_MODEL = "data_map_backend.user"
