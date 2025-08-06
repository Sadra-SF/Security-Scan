import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api_server.settings")

app = Celery("api_server")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Ensure tasks from all apps (including scans.*) are discovered
app.autodiscover_tasks([
    "scans",
    "core",
    "findings",
    "evidence",
    "projects",
    "targets",
    "reports",
    "schedules",
    "notifications",
    "integrations",
    "compliance",
    "health",
    "accounts",
    "api_server",
])

# Optional explicit route sanity (settings.CELERY_TASK_ROUTES governs routing)
@app.task(bind=True)
def ping(self):
    return "pong"