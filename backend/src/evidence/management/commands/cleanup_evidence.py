from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
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
        dry_run = options['dry_run']
        force = options['force']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Get evidence to delete by age
        age_queryset = Evidence.objects.filter(
            created_at__lt=cutoff_date
        ).exclude(file='')

        age_count = age_queryset.count()
        age_size = age_queryset.aggregate(
            total_size=Sum('size')
        )['total_size'] or 0

        # Get evidence to delete by size limit (if specified)
        size_queryset = Evidence.objects.none()
        if max_size_mb:
            max_size_bytes = max_size_mb * 1024 * 1024
            current_total = Evidence.objects.exclude(file='').aggregate(
                total_size=Sum('size')
            )['total_size'] or 0

            if current_total > max_size_bytes:
                # Delete oldest files first until we're under the limit
                size_queryset = Evidence.objects.exclude(file='').order_by('created_at')
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