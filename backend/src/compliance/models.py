import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class ComplianceFramework(models.Model):
    """Compliance frameworks like OWASP Top Ten, PCI DSS, HIPAA, etc."""

    class FrameworkType(models.TextChoices):
        OWASP_TOP_TEN = "owasp_top_ten", "OWASP Top Ten"
        PCI_DSS = "pci_dss", "PCI DSS"
        HIPAA = "hipaa", "HIPAA"
        GDPR = "gdpr", "GDPR"
        ISO_27001 = "iso_27001", "ISO 27001"
        NIST = "nist", "NIST"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    type = models.CharField(max_length=32, choices=FrameworkType.choices)
    version = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type", "name"]
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_type_display()} {self.version} - {self.name}"


class ComplianceControl(models.Model):
    """Individual controls within compliance frameworks."""

    class ControlType(models.TextChoices):
        REQUIREMENT = "requirement", "Requirement"
        CONTROL = "control", "Control"
        BEST_PRACTICE = "best_practice", "Best Practice"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    framework = models.ForeignKey(ComplianceFramework, on_delete=models.CASCADE, related_name="controls")
    control_id = models.CharField(max_length=64)  # e.g., "A1:2017", "2.1", "164.308"
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=16, choices=ControlType.choices, default=ControlType.REQUIREMENT)
    severity = models.CharField(max_length=16, choices=[
        ("info", "Info"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical")
    ], default="medium")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["framework", "control_id"]
        constraints = [
            models.UniqueConstraint(fields=["framework", "control_id"], name="uniq_control_framework_id"),
        ]
        indexes = [
            models.Index(fields=["framework", "control_id"]),
            models.Index(fields=["type"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.framework.name}:{self.control_id} - {self.title}"


class ComplianceTag(models.Model):
    """Legacy tag system - kept for backward compatibility."""
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


class ComplianceMapping(models.Model):
    """Maps findings to compliance controls."""

    class MappingType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    control = models.ForeignKey(ComplianceControl, on_delete=models.CASCADE, related_name="mappings")
    finding_type = models.CharField(max_length=128)  # e.g., "sql_injection", "xss", "weak_ssl"
    finding_pattern = models.CharField(max_length=255, blank=True)  # regex pattern for matching
    mapping_type = models.CharField(max_length=16, choices=MappingType.choices, default=MappingType.AUTOMATIC)
    confidence = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)], default=80)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["control", "finding_type"]
        constraints = [
            models.UniqueConstraint(fields=["control", "finding_type"], name="uniq_mapping_control_finding"),
        ]
        indexes = [
            models.Index(fields=["finding_type"]),
            models.Index(fields=["mapping_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.control} -> {self.finding_type}"


class ComplianceAssessment(models.Model):
    """Tracks compliance status for targets/projects."""

    class AssessmentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class ComplianceStatus(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"
        PARTIALLY_COMPLIANT = "partially_compliant", "Partially Compliant"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    framework = models.ForeignKey(ComplianceFramework, on_delete=models.CASCADE, related_name="assessments")
    target = models.ForeignKey("targets.Target", on_delete=models.CASCADE, related_name="compliance_assessments")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="compliance_assessments")
    assessment_status = models.CharField(max_length=16, choices=AssessmentStatus.choices, default=AssessmentStatus.PENDING)
    compliance_status = models.CharField(max_length=20, choices=ComplianceStatus.choices, default=ComplianceStatus.UNKNOWN)
    overall_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    control_scores = models.JSONField(default=dict, blank=True)  # {control_id: score}
    findings_count = models.JSONField(default=dict, blank=True)  # {severity: count}
    last_assessed_at = models.DateTimeField(null=True, blank=True)
    next_assessment_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_assessed_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["framework", "target"], name="uniq_assessment_framework_target"),
        ]
        indexes = [
            models.Index(fields=["framework", "assessment_status"]),
            models.Index(fields=["target", "compliance_status"]),
            models.Index(fields=["project", "assessment_status"]),
            models.Index(fields=["last_assessed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.framework.name} Assessment for {self.target} - {self.get_compliance_status_display()}"