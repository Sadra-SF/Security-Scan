from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from projects.models import Project
from targets.models import Target
from schedules.models import Schedule
from schedules.tasks import enqueue_due_scans, compute_next_run
from scans.models import Scan


class EnqueueDueScansTest(TestCase):
    def setUp(self):
        # Minimal project/target for schedules
        from django.contrib.auth import get_user_model

        # Create a project via direct create to satisfy FK; projects app has minimal fields
        self.project = Project.objects.create(
            id=1,
            organization_id=1,
            name="proj",
            slug="proj",
            description="",
        )
        self.target = Target.objects.create(
            project=self.project,
            name="example",
            slug="example",
            type=Target.TargetType.WEB,
            address="https://example.com",
        )

    @patch("schedules.tasks.start_scan.delay")
    def test_hourly_schedule_enqueues_once_and_advances(self, mock_delay):
        # Freeze now
        now = timezone.now().replace(second=0, microsecond=0)

        # Create an hourly schedule using config.cadence
        sch = Schedule.objects.create(
            target=self.target,
            scanner="static",
            config={"cadence": "hourly"},
            enabled=True,
            # Make it due now
            next_run_at=now,
        )

        # Run task
        processed = enqueue_due_scans()
        self.assertEqual(processed, 1, "Should process one schedule")

        # A Scan row should be created
        self.assertEqual(Scan.objects.count(), 1)
        scan = Scan.objects.first()
        self.assertIsNotNone(scan)
        self.assertEqual(scan.type, Scan.ScanType.SCHEDULED)
        self.assertEqual(scan.status, Scan.Status.PENDING)

        # Task should be enqueued
        mock_delay.assert_called_once()

        # Schedule should advance by 1 hour
        sch.refresh_from_db()
        self.assertIsNotNone(sch.last_run_at)
        self.assertIsNotNone(sch.next_run_at)
        self.assertEqual((sch.next_run_at - now).total_seconds(), 3600.0)

        # Running again within the same minute should be idempotent (no new scan)
        processed2 = enqueue_due_scans()
        self.assertEqual(processed2, 0)
        self.assertEqual(Scan.objects.count(), 1)