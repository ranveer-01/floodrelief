"""Local development settings: SQLite, DEBUG on, no HTTPS assumptions."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env_bool, env_list

DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Print emails (password resets, notifications) to the runserver console.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Static files are served straight from static/ by the dev server.
INTERNAL_IPS = ["127.0.0.1"]
