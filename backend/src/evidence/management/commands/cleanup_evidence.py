from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.conf import settings
import logging

from evidence.models import Evidence

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old evidence files based on age and storage limits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete evidence older than this many days (default: 30)'
        )
        parser.add_argument(
            '--max-size',
            type=int,
            help='Maximum total evidence size in MB (optional)'
        )
        parser.add_argument(
            '--finding-status',
            type=str,
            choices=['open', 'acknowledged', 'fixed', 'false_positive', 'risk_accepted', 'suppressed'],
            help='Only clean evidence from findings with this status'
        )
        parser.add_argument(
            '--evidence-types',
            type=str,
            help='Comma-separated list of evidence types to clean (e.g., screenshot,log,request)'
        )
        parser.add_argument(
            '--correlation-groups',
            action='store_true',
            help='Clean entire correlation groups instead of individual evidence'
        )
        parser.add_argument(
            '--keep-recent',
            type=int,
            help='Keep at least N most recent evidence per finding'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        days = options['days']
        max_size_mb = options['max_size']
        finding_status = options.get('finding_status')
        evidence_types = options.get('evidence_types')
        correlation_groups = options['correlation_groups']
        keep_recent = options.get('keep_recent')
        dry_run = options['dry_run']
        force = options['force']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Build base queryset
        base_queryset = Evidence.objects.exclude(file='')

        # Apply filters
        if finding_status:
            from findings.models import Finding
            finding_ids = Finding.objects.filter(status=finding_status).values_list('id', flat=True)
            base_queryset = base_queryset.filter(finding_id__in=finding_ids)

        if evidence_types:
            types_list = [t.strip() for t in evidence_types.split(',')]
            base_queryset = base_queryset.filter(kind__in=types_list)

        # Get evidence to delete by age
        age_queryset = base_queryset.filter(created_at__lt=cutoff_date)

        # Apply keep_recent logic
        if keep_recent:
            age_queryset = self._apply_keep_recent(age_queryset, keep_recent)

        age_count = age_queryset.count()
        age_size = age_queryset.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        # Get evidence to delete by size limit (if specified)
        size_queryset = Evidence.objects.none()
        if max_size_mb:
            max_size_bytes = max_size_mb * 1024 * 1024
            current_total = base_queryset.aggregate(
                total_size=Sum('size')
            )['total_size'] or 0

            if current_total > max_size_bytes:
                # Delete oldest files first until we're under the limit
                size_queryset = base_queryset.order_by('created_at')
                cumulative_size = 0
                size_evidence_ids = []

                for evidence in size_queryset:
                    if cumulative_size + (evidence.size or 0) > (current_total - max_size_bytes):
                        size_evidence_ids.append(evidence.id)
                        cumulative_size += evidence.size or 0
                        if cumulative_size >= (current_total - max_size_bytes):
                            break

                size_queryset = Evidence.objects.filter(id__in=size_evidence_ids)

        size_count = size_queryset.count()
        size_size = size_queryset.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        # Handle correlation groups
        if correlation_groups:
            age_queryset = self._expand_correlation_groups(age_queryset)
            size_queryset = self._expand_correlation_groups(size_queryset)

        # Combine querysets (remove duplicates)
        all_to_delete = (age_queryset | size_queryset).distinct()
        total_count = all_to_delete.count()
        total_size = all_to_delete.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No evidence files to clean up.')
            )
            return

        # Show summary
        self.stdout.write(
            self.style.WARNING(
                f'Found {total_count} evidence files to delete '
                f'({total_size / (1024*1024):.2f} MB)'
            )
        )

        if age_count > 0:
            self.stdout.write(
                f'  - {age_count} files older than {days} days '
                f'({age_size / (1024*1024):.2f} MB)'
            )

        if size_count > 0:
            self.stdout.write(
                f'  - {size_count} files to meet {max_size_mb} MB limit '
                f'({size_size / (1024*1024):.2f} MB)'
            )

        # Confirm deletion
        if not dry_run and not force:
            confirm = input('Proceed with deletion? (y/N): ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write('Aborted.')
                return

        # Perform deletion
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run: Would delete {total_count} files '
                    f'({total_size / (1024*1024):.2f} MB)'
                )
            )
        else:
            deleted_count = 0
            deleted_size = 0

            for evidence in all_to_delete:
                try:
                    size = evidence.size or 0
                    evidence.delete()  # This will also delete the file
                    deleted_count += 1
                    deleted_size += size
                except Exception as e:
                    logger.error(f'Failed to delete evidence {evidence.id}: {e}')
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to delete evidence {evidence.id}: {e}'
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} evidence files '
                    f'({deleted_size / (1024*1024):.2f} MB)'
                )
            )

    def _apply_keep_recent(self, queryset, keep_recent):
        """Apply keep_recent logic to preserve recent evidence per finding."""
        # Get findings that have more than keep_recent evidence
        findings_with_excess = queryset.values('finding').annotate(
            evidence_count=models.Count('id')
        ).filter(evidence_count__gt=keep_recent).values_list('finding', flat=True)

        if not findings_with_excess:
            return queryset.none()

        # For each finding, keep only the most recent keep_recent evidence
        excess_evidence_ids = []
        for finding_id in findings_with_excess:
            finding_evidence = queryset.filter(finding_id=finding_id).order_by('-created_at')
            # Skip the first keep_recent, delete the rest
            excess_evidence_ids.extend(
                finding_evidence.values_list('id', flat=True)[keep_recent:]
            )

        return queryset.filter(id__in=excess_evidence_ids)

    def _expand_correlation_groups(self, queryset):
        """Expand queryset to include all evidence in correlation groups."""
        correlation_ids = queryset.exclude(correlation_id='').values_list(
            'correlation_id', flat=True
        ).distinct()

        if not correlation_ids:
            return queryset

        # Get all evidence in these correlation groups
        correlated_evidence = Evidence.objects.filter(correlation_id__in=correlation_ids)

        # Combine with original queryset
        return (queryset | correlated_evidence).distinct()