import uuid
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.name


class Project(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        INTERNAL = "internal", "Internal"
        PUBLIC = "public", "Public"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"], name="uniq_project_org_slug"
            ),
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_project_org_name"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "slug"]),
            models.Index(fields=["organization", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.slug}"