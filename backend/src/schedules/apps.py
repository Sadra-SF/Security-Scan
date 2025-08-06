from django.apps import AppConfig
from django.core.cache import cache


class SchedulesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "schedules"
    verbose_name = "Schedules"

    def ready(self):
        # Import signals to register post_save handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
        # Initialize minimal health metric if not set
        try:
            cache.add("schedules:last_enqueue_run_at", "never", timeout=None)
        except Exception:
            pass