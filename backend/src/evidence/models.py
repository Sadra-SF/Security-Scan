import uuid
from django.db import models
from django.utils import timezone
from findings.models import Finding


class Evidence(models.Model):
    class Kind(models.TextChoices):
        SCREENSHOT = "screenshot", "Screenshot"
        LOG = "log", "Log"
        REQUEST = "request", "Request"
        RESPONSE = "response", "Response"
        ARTIFACT = "artifact", "Artifact"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding, on_delete=models.CASCADE, related_name="evidence", null=True, blank=True
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    storage_url = models.CharField(max_length=1000, help_text="Storage URL or path to the evidence blob")
    content_type = models.CharField(max_length=128, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, help_text="Hash of content if available")
    request_id = models.CharField(max_length=128, blank=True)
    response_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Evidence {self.id} ({self.kind})"