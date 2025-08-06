import os
from django.test import TestCase, override_settings
from django.utils import timezone

from projects.models import Project
from reports.models import Report
from reports.tasks import generate_report


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ReportGenerationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", description="Demo")

    def test_generate_report_csv_eager(self):
        report = Report.objects.create(
            project=self.project,
            title="CSV Report",
            format="csv",
            status=Report.Status.DRAFT,
            filters={},
        )
        # Run task synchronously
        generate_report(str(report.id))

        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.READY)
        self.assertTrue(report.storage_url)
        self.assertTrue(os.path.exists(report.storage_url))
        self.assertTrue(report.storage_url.endswith(".csv"))
        self.assertIsNotNone(report.generated_at)

    def test_generate_report_pdf_or_html_fallback_eager(self):
        report = Report.objects.create(
            project=self.project,
            title="PDF Report",
            format="pdf",
            status=Report.Status.DRAFT,
            filters={},
        )
        generate_report(str(report.id))

        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.READY)
        self.assertTrue(report.storage_url)
        self.assertTrue(os.path.exists(report.storage_url))
        # Could be .pdf when WeasyPrint available, else .html fallback
        self.assertTrue(report.storage_url.endswith(".pdf") or report.storage_url.endswith(".html"))
        self.assertIsNotNone(report.generated_at)