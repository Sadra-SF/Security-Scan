import uuid
from django.db import models
from django.utils import timezone
from projects.models import Project


class Report(models.Model):
    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        HTML = "html", "HTML"
        MD = "md", "Markdown"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports")
    title = models.CharField(max_length=255)
    version = models.CharField(max_length=32, blank=True)
    template = models.CharField(max_length=128, blank=True)
    format = models.CharField(max_length=8, choices=Format.choices, default=Format.PDF)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    storage_url = models.CharField(max_length=1000, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-generated_at", "-created_at"]
        indexes = [
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["format"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_format_display()})"