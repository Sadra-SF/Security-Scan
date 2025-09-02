from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from schedules.models import Schedule
from schedules.tasks import enqueue_due_scans


class Command(BaseCommand):
    help = "Manually execute a schedule by ID, creating a scan immediately."

    def add_arguments(self, parser):
        parser.add_argument(
            "schedule_id",
            type=str,
            help="UUID of the schedule to execute",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force execution even if schedule is disabled or in maintenance window",
        )

    def handle(self, *args, **options):
        schedule_id = options["schedule_id"]
        force = options["force"]

        try:
            schedule = Schedule.objects.select_related("target").get(id=schedule_id)
        except Schedule.DoesNotExist:
            raise CommandError(f"Schedule with ID {schedule_id} does not exist")

        if not schedule.enabled and not force:
            raise CommandError(f"Schedule {schedule_id} is disabled. Use --force to override.")

        self.stdout.write(
            self.style.SUCCESS(f"Executing schedule: {schedule}")
        )
        self.stdout.write(f"Target: {schedule.target}")
        self.stdout.write(f"Scanner: {schedule.scanner}")

        # Temporarily set next_run_at to now to make it "due"
        original_next_run = schedule.next_run_at
        now = timezone.now()

        if not force:
            # Check if in maintenance window
            from schedules.tasks import _in_maintenance_window
            if _in_maintenance_window(schedule, now):
                raise CommandError(
                    f"Schedule {schedule_id} is currently in maintenance window. "
                    "Use --force to override."
                )

        # Force the schedule to be due by setting next_run_at to past
        schedule.next_run_at = now
        schedule.save(update_fields=["next_run_at"])

        try:
            # Run the enqueue task for this specific schedule
            processed = enqueue_due_scans()
            if processed > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully triggered scan for schedule {schedule_id}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"No scans were processed for schedule {schedule_id}")
                )
        except Exception as e:
            # Restore original next_run_at
            schedule.next_run_at = original_next_run
            schedule.save(update_fields=["next_run_at"])
            raise CommandError(f"Failed to execute schedule: {e}")
        finally:
            # Always restore the original next_run_at if it wasn't None
            if original_next_run is not None:
                schedule.next_run_at = original_next_run
                schedule.save(update_fields=["next_run_at"])