import os

from django.apps import AppConfig


class LegacyBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'legacy_backend'
    verbose_name = "Legacy Backend"
