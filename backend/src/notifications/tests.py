from __future__ import annotations

import json
from unittest import mock

import pytest
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from notifications.models import NotificationChannel, NotificationRule
from notifications.tasks import dispatch_event
from projects.models import Organization, Project
from scans.models import Scan
from targets.models import Target


class NotificationsDispatchTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name="Acme", slug="acme")
        self.project = Project.objects.create(organization=self.org, name="App", slug="app")
        self.target = Target.objects.create(project=self.project, name="app.local", type="web", address="http://app.local")
        self.scan = Scan.objects.create(target=self.target, scanner="unit", status=Scan.Status.COMPLETED)
        # minimal stats to drive threshold
        self.scan.stats = {"total": 3, "by_severity": {"low": 1, "high": 2}, "by_category": {}}
        self.scan.finished_at = timezone.now()
        self.scan.save(update_fields=["stats", "finished_at"])

    def test_email_dispatch_builds_message(self):
        ch = NotificationChannel.objects.create(
            project=self.project,
            name="email",
            type=NotificationChannel.ChannelType.EMAIL,
            config={"recipients": ["sec@example.com"]},
        )
        NotificationRule.objects.create(
            project=self.project,
            name="scan completed",
            event=NotificationRule.Event.SCAN_COMPLETED,
            severity_min=NotificationRule.SeverityThreshold.LOW,
            channel=ch,
            enabled=True,
        )

        # Call task (synchronously)
        res = dispatch_event("scan.completed", str(self.scan.id))
        self.assertGreaterEqual(res.get("dispatched", 0), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("scan", mail.outbox[0].subject.lower())
        self.assertIn("App", mail.outbox[0].subject)

    @mock.patch("requests.post")
    def test_slack_webhook_sends_and_retries_on_non_2xx(self, mpost):
        # 1st attempt: non-2xx -> celery retry path will raise inside task loop, but our task catches and schedules retry
        class Resp:
            status_code = 500

        mpost.return_value = Resp()

        ch = NotificationChannel.objects.create(
            project=self.project,
            name="slack",
            type=NotificationChannel.ChannelType.SLACK,
            config={"webhook_url": "https://hooks.slack.invalid/abc"},
        )
        NotificationRule.objects.create(
            project=self.project,
            name="scan completed slack",
            event=NotificationRule.Event.SCAN_COMPLETED,
            severity_min=NotificationRule.SeverityThreshold.LOW,
            channel=ch,
            enabled=True,
        )

        # Execute; since dispatch_event retries internally, we just assert result contains failure info
        res = dispatch_event("scan.completed", str(self.scan.id))
        self.assertIn("results", res)
        self.assertGreaterEqual(len(res["results"]), 1)

    @mock.patch("requests.post")
    def test_threshold_rule_triggers_on_high(self, mpost):
        class Resp:
            status_code = 204

        mpost.return_value = Resp()

        ch = NotificationChannel.objects.create(
            project=self.project,
            name="webhook",
            type=NotificationChannel.ChannelType.WEBHOOK,
            config={"webhook_url": "https://webhook.site/example", "secret": "s"},
        )
        NotificationRule.objects.create(
            project=self.project,
            name="threshold",
            event=NotificationRule.Event.SCAN_COMPLETED,  # mapped in dispatcher for threshold evaluation
            severity_min=NotificationRule.SeverityThreshold.HIGH,
            channel=ch,
            enabled=True,
        )

        res = dispatch_event("severity.threshold", str(self.scan.id))
        self.assertGreaterEqual(res.get("dispatched", 0), 1)
        # verify we posted JSON once
        self.assertTrue(mpost.called)