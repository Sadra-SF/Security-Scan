import os
import uuid
import logging
from datetime import datetime
from typing import Dict

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Report
from .utils import (
    ensure_reports_storage_dir,
    findings_queryset_with_compliance,
    write_findings_csv_to_temp,
    move_temp_to_reports_storage,
    render_report_html,
)

logger = logging.getLogger(__name__)


def _build_context(report: Report, qs):
    """
    Build rendering context for templates/exports.
    Groups findings by severity and category, and provides project/filters metadata.
    """
    # Simple grouping in-memory; could be improved using aggregation if needed
    grouped = {}
    for f in qs.iterator(chunk_size=1000):
        severity = f.severity or "unknown"
        category = ""
        if isinstance(f.metadata, dict):
            category = f.metadata.get("category") or "uncategorized"
        grouped.setdefault(severity, {})
        grouped[severity].setdefault(category, [])
        grouped[severity][category].append(f)

    return {
        "report": report,
        "project": report.project,
        "filters": report.filters or {},
        "generated_at": timezone.now(),
        "findings": qs,
        "grouped": grouped,
    }


def _write_html_fallback(content: str) -> str:
    """
    When WeasyPrint is unavailable but format requested is pdf, write HTML fallback.
    Returns absolute file path to stored file.
    """
    ensure_reports_storage_dir()
    name = f"{uuid.uuid4()}.html"
    abs_path = os.path.join(settings.REPORTS_STORAGE_DIR, name)
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return abs_path


@shared_task(name="reports.tasks.generate_report")
def generate_report(report_id: str) -> None:
    """
    Celery task to generate a report. Supports 'pdf' and 'csv'.
    - For csv: write via temp file then move into storage, set storage_url.
    - For pdf: render HTML template and, if WeasyPrint available, render to PDF.
      Otherwise, store the HTML fallback with .html extension.
    Updates status and generated_at.
    """
    try:
        report = Report.objects.select_related("project").get(id=report_id)
    except Report.DoesNotExist:
        logger.error("Report %s does not exist", report_id)
        return

    with transaction.atomic():
        report.status = Report.Status.GENERATING
        report.generated_at = timezone.now()
        report.save(update_fields=["status", "generated_at", "updated_at"])

    try:
        filters: Dict = report.filters or {}
        qs = findings_queryset_with_compliance(filters)

        fmt = (report.format or "pdf").lower()
        storage_abs_path = None

        if fmt == "csv":
            temp_path, _count = write_findings_csv_to_temp(qs)
            final_name = f"{report.id}.csv"
            storage_abs_path = move_temp_to_reports_storage(temp_path, final_name)
        elif fmt == "html":
            # Generate HTML report
            template_name = report.template or "reports/html/scan_report.html"
            context = _build_context(report, qs)
            html = render_report_html(template_name, context)
            storage_abs_path = _write_html_fallback(html)
        elif fmt == "md":
            # Generate Markdown report
            template_name = report.template or "reports/md/scan_report.md"
            context = _build_context(report, qs)
            md_content = render_report_html(template_name, context)  # Reuse HTML renderer for simplicity
            ensure_reports_storage_dir()
            name = f"{report.id}.md"
            abs_path = os.path.join(settings.REPORTS_STORAGE_DIR, name)
            with open(abs_path, "w", encoding="utf-8") as fh:
                fh.write(md_content)
            storage_abs_path = abs_path
        else:
            # Default to PDF
            template_name = report.template or "reports/pdf/scan_report.html"
            context = _build_context(report, qs)
            html = render_report_html(template_name, context)

            if getattr(settings, "WEASYPRINT_AVAILABLE", False):
                try:
                    from weasyprint import HTML  # type: ignore

                    out_name = f"{report.id}.pdf"
                    out_abs = os.path.join(ensure_reports_storage_dir(), out_name)
                    HTML(string=html).write_pdf(out_abs)
                    storage_abs_path = out_abs
                except Exception as we:
                    logger.warning("WeasyPrint failed, falling back to HTML for report %s: %s", report.id, we)
                    storage_abs_path = _write_html_fallback(html)
            else:
                storage_abs_path = _write_html_fallback(html)

        # Compute storage_url; for local storage we expose absolute path, or a relative file URL.
        storage_url = storage_abs_path

        with transaction.atomic():
            report.status = Report.Status.READY
            report.storage_url = storage_url
            report.generated_at = timezone.now()
            report.save(update_fields=["status", "storage_url", "generated_at", "updated_at"])

        logger.info("Report %s generated at %s", report.id, storage_url)
    except Exception as e:
        logger.exception("Failed to generate report %s: %s", report.id, e)
        with transaction.atomic():
            report.status = Report.Status.FAILED
            report.save(update_fields=["status", "updated_at"])