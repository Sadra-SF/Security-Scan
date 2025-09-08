from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Sum, Q
from django.conf import settings
import os
import shutil
import logging
import gzip
from pathlib import Path

from evidence.models import Evidence

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Archive old evidence files to compressed storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Archive evidence older than this many days (default: 90)'
        )
        parser.add_argument(
            '--archive-path',
            type=str,
            help='Path to store archived files (default: ARCHIVE_ROOT from settings)'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress archived files with gzip'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived without actually archiving'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--finding-status',
            type=str,
            choices=['fixed', 'false_positive', 'risk_accepted', 'suppressed'],
            help='Only archive evidence from findings with this status'
        )
        parser.add_argument(
            '--evidence-types',
            type=str,
            help='Comma-separated list of evidence types to archive (e.g., screenshot,log,request)'
        )

    def handle(self, *args, **options):
        days = options['days']
        archive_path = options.get('archive_path') or getattr(settings, 'ARCHIVE_ROOT', 'archives')
        compress = options['compress']
        dry_run = options['dry_run']
        force = options['force']
        finding_status = options.get('finding_status')
        evidence_types = options.get('evidence_types')

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Build queryset
        queryset = Evidence.objects.filter(
            created_at__lt=cutoff_date
        ).exclude(file='')

        # Filter by finding status if specified
        if finding_status:
            from findings.models import Finding
            finding_ids = Finding.objects.filter(status=finding_status).values_list('id', flat=True)
            queryset = queryset.filter(finding_id__in=finding_ids)

        # Filter by evidence types if specified
        if evidence_types:
            types_list = [t.strip() for t in evidence_types.split(',')]
            queryset = queryset.filter(kind__in=types_list)

        evidence_count = queryset.count()
        total_size = queryset.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        if evidence_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No evidence files to archive.')
            )
            return

        # Create archive directory
        archive_dir = Path(archive_path) / f"evidence_archive_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        if not dry_run:
            try:
                archive_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise CommandError(f"Failed to create archive directory {archive_dir}: {e}")

        # Show summary
        self.stdout.write(
            self.style.WARNING(
                f'Found {evidence_count} evidence files to archive '
                f'({total_size / (1024*1024):.2f} MB)'
            )
        )
        self.stdout.write(f'Archive location: {archive_dir}')

        if finding_status:
            self.stdout.write(f'Filtering by finding status: {finding_status}')

        if evidence_types:
            self.stdout.write(f'Filtering by evidence types: {evidence_types}')

        # Confirm archiving
        if not dry_run and not force:
            confirm = input('Proceed with archiving? (y/N): ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Aborted.')
                return

        # Perform archiving
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run: Would archive {evidence_count} files '
                    f'({total_size / (1024*1024):.2f} MB)'
                )
            )
        else:
            archived_count = 0
            archived_size = 0
            errors = []

            for evidence in queryset:
                try:
                    # Archive the file
                    success, archived_path, file_size = self._archive_file(
                        evidence, archive_dir, compress
                    )

                    if success:
                        # Update evidence record
                        evidence.storage_url = str(archived_path)
                        evidence.metadata['archived_at'] = timezone.now().isoformat()
                        evidence.metadata['original_file'] = evidence.file.name if evidence.file else None
                        # Delete the original file
                        evidence.delete_file()
                        evidence.save(update_fields=['storage_url', 'metadata'])

                        archived_count += 1
                        archived_size += file_size

                        self.stdout.write(
                            f'Archived: {evidence.id} -> {archived_path}'
                        )
                    else:
                        errors.append(f"Failed to archive {evidence.id}")

                except Exception as e:
                    logger.error(f'Failed to archive evidence {evidence.id}: {e}')
                    errors.append(f"Failed to archive {evidence.id}: {e}")

            # Show results
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully archived {archived_count} evidence files '
                    f'({archived_size / (1024*1024):.2f} MB)'
                )
            )

            if errors:
                self.stdout.write(
                    self.style.ERROR(f'Errors encountered: {len(errors)}')
                )
                for error in errors[:5]:  # Show first 5 errors
                    self.stdout.write(f'  - {error}')
                if len(errors) > 5:
                    self.stdout.write(f'  ... and {len(errors) - 5} more')

    def _archive_file(self, evidence, archive_dir, compress):
        """Archive a single evidence file."""
        if not evidence.file or not evidence.file.path:
            return False, None, 0

        source_path = Path(evidence.file.path)
        if not source_path.exists():
            return False, None, 0

        # Create archive path
        relative_path = source_path.relative_to(settings.MEDIA_ROOT)
        archive_path = archive_dir / relative_path

        # Create subdirectories if needed
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy or compress file
        if compress:
            archive_path = archive_path.with_suffix(archive_path.suffix + '.gz')
            with source_path.open('rb') as src:
                with gzip.open(str(archive_path), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        else:
            shutil.copy2(source_path, archive_path)

        # Get file size
        file_size = archive_path.stat().st_size

        return True, archive_path, file_size