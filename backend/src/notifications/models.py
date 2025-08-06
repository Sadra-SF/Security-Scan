import uuid
from django.db import models
from django.utils import timezone
from projects.models import Project


class NotificationChannel(models.Model):
    class ChannelType(models.TextChoices):
        EMAIL = "email", "Email"
        SLACK = "slack", "Slack"
        WEBHOOK = "webhook", "Webhook"
        MS_TEAMS = "ms_teams", "Microsoft Teams"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notification_channels")
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=16, choices=ChannelType.choices)
    config = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__organization__name", "project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_notify_channel_project_name"),
        ]
        indexes = [
            models.Index(fields=["project", "type"]),
            models.Index(fields=["enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.project}::{self.name} [{self.type}]"


class NotificationRule(models.Model):
    class Event(models.TextChoices):
        SCAN_COMPLETED = "scan_completed", "Scan Completed"
        FINDING_CREATED = "finding_created", "Finding Created"
        FINDING_UPDATED = "finding_updated", "Finding Updated"

    class SeverityThreshold(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notification_rules")
    name = models.CharField(max_length=128)
    event = models.CharField(max_length=32, choices=Event.choices)
    severity_min = models.CharField(max_length=16, choices=SeverityThreshold.choices, default=SeverityThreshold.LOW)
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE, related_name="rules")
    enabled = models.BooleanField(default=True)
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__organization__name", "project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_notify_rule_project_name"),
        ]
        indexes = [
            models.Index(fields=["project", "event"]),
            models.Index(fields=["enabled"]),
            models.Index(fields=["severity_min"]),
        ]

    def __str__(self) -> str:
        return f"{self.project}::{self.name} ({self.event})"