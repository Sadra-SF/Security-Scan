from __future__ import annotations

from django.db import models


class Asset(models.Model):
    TYPE_CHOICES = [
        ("web", "Web URL"),
        ("host", "Host/IP"),
        ("network", "Network/CIDR"),
        ("url", "URL"),
        ("cidr", "CIDR"),
        ("ip", "IP Address"),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    url_or_cidr = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.type})"


class ScanProfile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    enabled_scanners = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ScanRun(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="scan_runs")
    profile = models.ForeignKey(ScanProfile, on_delete=models.PROTECT, related_name="scan_runs")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"ScanRun#{self.pk} {self.status}"