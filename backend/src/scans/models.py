import uuid
from django.db import models
from django.utils import timezone
from targets.models import Target


class Scan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    class ScanType(models.TextChoices):
        ACTIVE = "active", "Active"
        PASSIVE = "passive", "Passive"
        SCHEDULED = "scheduled", "Scheduled"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="scans")
    scanner = models.CharField(max_length=64, help_text="Scanner backend identifier, e.g., zap, nuclei")
    type = models.CharField(max_length=16, choices=ScanType.choices, default=ScanType.MANUAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    config = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    stats = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["target", "started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Scan {self.id} on {self.target} ({self.status})"