import uuid
from django.db import models
from django.utils import timezone
from projects.models import Project


class IntegrationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="integration_tokens")
    name = models.CharField(max_length=128)
    token_hash = models.CharField(max_length=128, db_index=True, help_text="Hashed token. Raw token is never stored.")
    scopes = models.JSONField(default=list, blank=True, help_text="List of scopes/permissions")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["project__organization__name", "project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_integration_token_project_name"),
        ]
        indexes = [
            models.Index(fields=["project", "name"]),
            models.Index(fields=["project", "token_hash"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.project}::{self.name}"


class Webhook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="webhooks")
    name = models.CharField(max_length=128)
    url = models.URLField(max_length=1000)
    secret_hash = models.CharField(max_length=128, blank=True, help_text="Hashed shared secret for signature verification")
    headers = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["project__organization__name", "project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_webhook_project_name"),
        ]
        indexes = [
            models.Index(fields=["project", "enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.project}::{self.name}"