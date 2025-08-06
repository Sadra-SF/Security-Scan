import uuid
from django.db import models
from django.utils import timezone


class ComplianceTag(models.Model):
    slug = models.SlugField(primary_key=True, max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=64, default="OWASP")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "slug"]
        indexes = [
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return f"{self.category}:{self.slug} - {self.title}"