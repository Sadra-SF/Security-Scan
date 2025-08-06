import uuid
from django.db import models
from django.utils import timezone
from projects.models import Project


class Target(models.Model):
    class TargetType(models.TextChoices):
        WEB = "web", "Web"
        API = "api", "API"
        HOST = "host", "Host"
        MOBILE = "mobile", "Mobile"
        REPO = "repo", "Repository"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="targets")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    type = models.CharField(max_length=16, choices=TargetType.choices, default=TargetType.WEB)
    address = models.CharField(max_length=500, help_text="Hostname, URL, IP/CIDR, package name, or identifier")
    tags = models.JSONField(default=list, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project__organization__name", "project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "slug"], name="uniq_target_project_slug"),
        ]
        indexes = [
            models.Index(fields=["project", "slug"]),
            models.Index(fields=["project", "name"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self) -> str:
        return f"{self.project}/{self.slug}"