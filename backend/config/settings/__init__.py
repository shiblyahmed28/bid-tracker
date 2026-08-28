"""Default settings module — dev, matches the previous single-file config.settings
exactly. Production deployments set DJANGO_SETTINGS_MODULE=config.settings.production
instead (see production.py)."""

from .base import *  # noqa: F401,F403
