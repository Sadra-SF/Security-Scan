import uuid
import os
import logging
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.files.storage import default_storage
from findings.models import Finding
from typing import Optional

logger = logging.getLogger(__name__)


def evidence_upload_path(instance, filename):
    """Generate upload path for evidence files."""
    if instance.finding:
        # Path: evidence/{finding_id}/{kind}/{uuid}_{filename}
        return f"evidence/{instance.finding.id}/{instance.kind}/{instance.id}_{filename}"
    else:
        # Path: evidence/standalone/{kind}/{uuid}_{filename}
        return f"evidence/standalone/{instance.kind}/{instance.id}_{filename}"


class Evidence(models.Model):
    class Kind(models.TextChoices):
        SCREENSHOT = "screenshot", "Screenshot"
        LOG = "log", "Log"
        REQUEST = "request", "Request"
        RESPONSE = "response", "Response"
        REQUEST_RESPONSE = "request_response", "Request/Response"
        ARTIFACT = "artifact", "Artifact"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(
        Finding, on_delete=models.CASCADE, related_name="evidence", null=True, blank=True
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    # File storage
    file = models.FileField(
        upload_to=evidence_upload_path,
        storage=default_storage,
        null=True,
        blank=True,
        help_text="Uploaded evidence file"
    )
    # Alternative storage (URL or external path)
    storage_url = models.CharField(
        max_length=1000,
        blank=True,
        help_text="External storage URL or path to the evidence blob"
    )
    content_type = models.CharField(max_length=128, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, help_text="Hash of content if available")
    request_id = models.CharField(max_length=128, blank=True)
    response_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Enhanced correlation fields
    correlation_id = models.CharField(max_length=128, blank=True, help_text="ID for correlating related evidence")
    correlation_type = models.CharField(max_length=64, blank=True, help_text="Type of correlation (e.g., 'request_response', 'vulnerability_chain')")
    parent_evidence = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_evidence', help_text="Parent evidence for hierarchical relationships"
    )
    tags = models.JSONField(default=list, blank=True, help_text="Tags for evidence categorization and search")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["correlation_id"]),
            models.Index(fields=["correlation_type"]),
            models.Index(fields=["parent_evidence"]),
            models.Index(fields=["finding", "kind"]),
            models.Index(fields=["finding", "correlation_id"]),
        ]

    def __str__(self) -> str:
        return f"Evidence {self.id} ({self.kind})"

    @property
    def file_url(self):
        """Get the URL for the evidence file."""
        if self.file:
            return self.file.url
        elif self.storage_url:
            return self.storage_url
        return None

    @property
    def file_path(self):
        """Get the file path for the evidence file."""
        if self.file:
            return self.file.path
        elif self.storage_url and not self.storage_url.startswith(('http://', 'https://')):
            return self.storage_url
        return None

    def delete_file(self):
        """Delete the associated file from storage."""
        if self.file and default_storage.exists(self.file.name):
            self.file.delete(save=False)

    def save(self, *args, **kwargs):
        """Override save to handle file cleanup on updates."""
        # If updating and file is being changed, delete old file
        if self.pk:
            try:
                old_instance = Evidence.objects.get(pk=self.pk)
                if old_instance.file and old_instance.file != self.file:
                    old_instance.delete_file()
            except Evidence.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete to clean up files."""
        self.delete_file()
        return super().delete(*args, **kwargs)

    def verify_file_integrity(self):
        """Verify that the file exists and size matches."""
        if not self.file:
            return False, "No file associated"

        if not default_storage.exists(self.file.name):
            return False, "File does not exist in storage"

        try:
            # Check file size if available
            if self.size:
                actual_size = default_storage.size(self.file.name)
                if actual_size != self.size:
                    return False, f"Size mismatch: expected {self.size}, got {actual_size}"
            return True, "File integrity verified"
        except Exception as e:
            return False, f"Error checking file: {e}"

    @classmethod
    def get_storage_stats(cls):
        """Get storage statistics for all evidence files."""
        evidence_with_files = cls.objects.exclude(file='')

        total_count = evidence_with_files.count()
        total_size = evidence_with_files.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        by_kind = {}
        for evidence in evidence_with_files.values('kind').annotate(
            count=models.Count('id'),
            size=Sum('size')
        ):
            by_kind[evidence['kind']] = {
                'count': evidence['count'],
                'size': evidence['size'] or 0
            }

        return {
            'total_count': total_count,
            'total_size': total_size,
            'by_kind': by_kind
        }

    @classmethod
    def cleanup_orphaned_files(cls):
        """Remove files from storage that don't have corresponding Evidence records."""
        from django.core.files.storage import default_storage
        import os

        # This is a basic implementation - in production you'd want more sophisticated logic
        evidence_files = set()
        for evidence in cls.objects.exclude(file=''):
            if evidence.file and evidence.file.name:
                evidence_files.add(evidence.file.name)

        # Get all files in evidence directory
        try:
            dirs, files = default_storage.listdir('evidence')
            all_files = set()

            def collect_files(path):
                try:
                    subdirs, subfiles = default_storage.listdir(path)
                    for file in subfiles:
                        all_files.add(os.path.join(path, file))
                    for subdir in subdirs:
                        collect_files(os.path.join(path, subdir))
                except:
                    pass

            collect_files('evidence')

            orphaned = all_files - evidence_files
            deleted_count = 0

            for orphaned_file in orphaned:
                try:
                    default_storage.delete(orphaned_file)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete orphaned file {orphaned_file}: {e}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {e}")
            return 0

    @property
    def correlated_evidence(self):
        """Get all evidence correlated with this one."""
        if not self.correlation_id:
            return Evidence.objects.none()

        return Evidence.objects.filter(
            correlation_id=self.correlation_id
        ).exclude(id=self.id)

    @property
    def evidence_chain(self):
        """Get the full evidence chain including parent/child relationships."""
        chain = []
        current = self

        # Walk up the parent chain
        while current.parent_evidence:
            chain.insert(0, current.parent_evidence)
            current = current.parent_evidence

        chain.append(self)

        # Walk down the child chain
        children = list(Evidence.objects.filter(parent_evidence=self))
        while children:
            child = children.pop(0)
            chain.append(child)
            children.extend(list(Evidence.objects.filter(parent_evidence=child)))

        return chain

    def add_tag(self, tag: str):
        """Add a tag to this evidence."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=['tags'])

    def remove_tag(self, tag: str):
        """Remove a tag from this evidence."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=['tags'])

    @classmethod
    def correlate_evidence(cls, evidence_ids: list, correlation_type: str = "manual"):
        """Correlate multiple evidence items together."""
        if len(evidence_ids) < 2:
            return

        import uuid
        correlation_id = str(uuid.uuid4())

        cls.objects.filter(id__in=evidence_ids).update(
            correlation_id=correlation_id,
            correlation_type=correlation_type,
            updated_at=timezone.now()
        )

    @classmethod
    def get_evidence_by_correlation(cls, correlation_id: str):
        """Get all evidence with a specific correlation ID."""
        return cls.objects.filter(correlation_id=correlation_id)

    @classmethod
    def get_evidence_by_tags(cls, tags: list, match_all: bool = False):
        """Get evidence that has any or all of the specified tags."""
        if not tags:
            return cls.objects.none()

        if match_all:
            # Match evidence that has ALL specified tags
            queryset = cls.objects.all()
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
            return queryset
        else:
            # Match evidence that has ANY of the specified tags
            queryset = cls.objects.none()
            for tag in tags:
                queryset = queryset | cls.objects.filter(tags__contains=[tag])
            return queryset

    @classmethod
    def analyze_evidence_relationships(cls, finding_id: Optional[int] = None):
        """Analyze evidence relationships and return insights."""
        queryset = cls.objects.all()
        if finding_id:
            queryset = queryset.filter(finding_id=finding_id)

        total_evidence = queryset.count()
        correlated_groups = queryset.exclude(correlation_id='').values('correlation_id').distinct().count()
        tagged_evidence = queryset.exclude(tags=[]).count()
        evidence_with_parents = queryset.exclude(parent_evidence=None).count()

        return {
            'total_evidence': total_evidence,
            'correlated_groups': correlated_groups,
            'tagged_evidence': tagged_evidence,
            'evidence_with_parents': evidence_with_parents,
            'correlation_coverage': correlated_groups / max(total_evidence, 1),
            'hierarchy_coverage': evidence_with_parents / max(total_evidence, 1),
        }