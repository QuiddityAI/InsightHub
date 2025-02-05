import os

from django.apps import AppConfig


class DataMapBackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "data_map_backend"
    verbose_name = "Data Map Backend"

    def ready(self) -> None:
        # only initialize the monitoring when the server is started, not in tests or migrations:
        if os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN"):
            from data_map_backend.monitoring import register_collectors

            register_collectors()
