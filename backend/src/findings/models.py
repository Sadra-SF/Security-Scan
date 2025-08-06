import uuid
from django.db import models
from django.utils import timezone
from targets.models import Target
from scans.models import Scan


class Finding(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        FIXED = "fixed", "Fixed"
        FALSE_POSITIVE = "false_positive", "False Positive"
        RISK_ACCEPTED = "risk_accepted", "Risk Accepted"
        SUPPRESSED = "suppressed", "Suppressed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, on_delete=models.CASCADE, related_name="findings")
    scan = models.ForeignKey(Scan, on_delete=models.SET_NULL, null=True, blank=True, related_name="findings")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    cvss_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    dedupe_hash = models.CharField(max_length=64, help_text="Deterministic hash for deduplication within a target")
    locations = models.JSONField(default=list, blank=True, help_text="List of affected locations/paths/URLs")
    evidence_refs = models.JSONField(default=list, blank=True, help_text="IDs/refs of linked evidence (populated later)")
    metadata = models.JSONField(default=dict, blank=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-severity", "-last_seen_at"]
        constraints = [
            models.UniqueConstraint(fields=["target", "dedupe_hash"], name="uniq_finding_target_dedupe"),
        ]
        indexes = [
            models.Index(fields=["severity"]),
            models.Index(fields=["status"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.severity.upper()} - {self.title} ({self.target})"