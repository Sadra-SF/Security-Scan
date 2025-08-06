import uuid
from django.db import models
from django.utils import timezone
from targets.models import Target


class Schedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="schedules")

    # Cron-like separate fields
    minute = models.CharField(max_length=64, default="*")
    hour = models.CharField(max_length=64, default="*")
    day_of_week = models.CharField(max_length=64, default="*")
    day_of_month = models.CharField(max_length=64, default="*")
    month_of_year = models.CharField(max_length=64, default="*")

    scanner = models.CharField(max_length=64)
    config = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-next_run_at", "-created_at"]
        indexes = [
            models.Index(fields=["next_run_at", "enabled"]),
            models.Index(fields=["target"]),
            models.Index(fields=["scanner"]),
        ]

    def __str__(self) -> str:
        return f"Schedule {self.scanner} for {self.target} ({'enabled' if self.enabled else 'disabled'})"