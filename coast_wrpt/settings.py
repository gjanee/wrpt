# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

import os

import django_heroku

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.environ.get("WRPT_DEBUG", "0") == "1":
  DEBUG = True

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
  "django.contrib.admin",
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.messages",
  "django.contrib.sessions",
  "django.contrib.staticfiles",
  "wrpt"
]

MIDDLEWARE = [
  "django.middleware.common.CommonMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
  "django.contrib.messages.middleware.MessageMiddleware",
  "whitenoise.middleware.WhiteNoiseMiddleware"
]

ROOT_URLCONF = "coast_wrpt.urls"

WSGI_APPLICATION = "coast_wrpt.wsgi.application"

if os.environ.get("WRPT_USE_SQLITE3", "0") == "1":
  DATABASES = {
    "default": {
      "ENGINE": "django.db.backends.sqlite3",
      "NAME": os.path.join(BASE_DIR, "db.sqlite3")
    }
  }

TIME_ZONE = "America/Los_Angeles"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "coast_wrpt", "static")]
WHITENOISE_ROOT = os.path.join(BASE_DIR, "coast_wrpt", "static", "root")

TEMPLATES = [
  { "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [os.path.join(BASE_DIR, "coast_wrpt", "templates")],
    "APP_DIRS": True,
    "OPTIONS": {
      "context_processors": [
        "django.contrib.auth.context_processors.auth",
        "django.template.context_processors.i18n",
        "django.template.context_processors.request",
        "django.template.context_processors.tz",
        "django.contrib.messages.context_processors.messages"
      ],
    },
  }
]

AUTHENTICATION_BACKENDS = ["wrpt.auth_backends.WrptUserModelBackend"]

LOGGING = {
  "version": 1,
  "disable_existing_loggers": False,
  "handlers": {
    "console": { "class": "logging.StreamHandler" }
  },
  "loggers": {
    "django": { "handlers": ["console"], "level": "ERROR" },
    "wrpt": { "handlers": ["console"], "level": "INFO" }
  }
}

django_heroku.settings(locals(), logging=False)
