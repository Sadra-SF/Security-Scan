import uuid
import os
import logging
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.files.storage import default_storage
from findings.models import Finding

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