import csv
import os
import shutil
import tempfile
from datetime import timedelta
from typing import Iterable, List, Optional, Tuple

from django.conf import settings
from django.db.models import Prefetch, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone

from findings.models import Finding
from scans.models import Scan
from targets.models import Target

# Storage helper


def ensure_reports_storage_dir() -> str:
    """
    Resolve the reports storage directory from settings.REPORTS_STORAGE_DIR,
    falling back to MEDIA_ROOT/reports, and ensure it exists.
    """
    base = getattr(settings, "REPORTS_STORAGE_DIR", None)
    if not base:
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            # Default to BASE_DIR/var/reports if MEDIA_ROOT is not set
            base = str(getattr(settings, "BASE_DIR", ".") / "var" / "reports")  # type: ignore
        else:
            base = os.path.join(media_root, "reports")
    os.makedirs(base, exist_ok=True)
    return base


def findings_queryset_with_compliance(filters: dict) -> QuerySet:
    """
    Build a queryset for findings based on provided filters.

    Supported filter keys:
      - project_id, target_id, scan_id
      - severity (list or str), status (list or str), category (list or str) via metadata["category"]
      - created_since_days (int), last_seen_since_days (int)
    """
    qs = Finding.objects.select_related(
        "target",
        "target__project",
        "scan",
    ).all()

    # Compliance tags relationship may live on another app (compliance)
    # If M2M exists (through related_name 'compliance_tags'), prefetch; otherwise ignore gracefully.
    try:
        from compliance.models import ComplianceTag  # type: ignore

        qs = qs.prefetch_related(Prefetch("compliancetag_set", queryset=ComplianceTag.objects.all()))
    except Exception:
        # Try generic m2m name 'compliance_tags'
        try:
            qs = qs.prefetch_related("compliance_tags")
        except Exception:
            # No compliance tagging present; proceed without prefetch.
            pass

    project_id = filters.get("project_id")
    target_id = filters.get("target_id")
    scan_id = filters.get("scan_id")

    if project_id:
        qs = qs.filter(target__project_id=project_id)
    if target_id:
        qs = qs.filter(target_id=target_id)
    if scan_id:
        qs = qs.filter(scan_id=scan_id)

    def _as_list(val) -> Optional[List[str]]:
        if val is None:
            return None
        if isinstance(val, (list, tuple, set)):
            return list(val)
        return [str(val)]

    severities = _as_list(filters.get("severity"))
    statuses = _as_list(filters.get("status"))
    categories = _as_list(filters.get("category"))

    if severities:
        qs = qs.filter(severity__in=severities)
    if statuses:
        qs = qs.filter(status__in=statuses)
    if categories:
        # Assuming category may be stored inside metadata with key 'category'
        qs = qs.filter(metadata__category__in=categories)

    created_since_days = filters.get("created_since_days")
    if isinstance(created_since_days, int) and created_since_days >= 0:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=created_since_days))

    last_seen_since_days = filters.get("last_seen_since_days")
    if isinstance(last_seen_since_days, int) and last_seen_since_days >= 0:
        qs = qs.filter(last_seen_at__gte=timezone.now() - timedelta(days=last_seen_since_days))

    return qs


def finding_to_csv_row(f) -> List[str]:
    """
    Produce CSV row for a finding with columns:
    id, title, severity, category, url/file, param, first_seen, last_seen, status,
    compliance_tags (joined), plugin_key, scan_id, target_id
    """
    # Extract location info heuristically from locations JSON
    url_or_file = ""
    param = ""
    if isinstance(f.locations, list) and f.locations:
        loc = f.locations[0] or {}
        if isinstance(loc, dict):
            url_or_file = loc.get("url") or loc.get("file") or ""
            param = loc.get("param") or ""
        else:
            url_or_file = str(loc)

    # Category from metadata
    category = ""
    if isinstance(f.metadata, dict):
        category = f.metadata.get("category") or ""

    # Compliance tags, try multiple attribute names
    tags: List[str] = []
    # Try 'compliance_tags' m2m
    if hasattr(f, "compliance_tags"):
        try:
            tags = [t.slug if hasattr(t, "slug") else getattr(t, "name", str(t)) for t in f.compliance_tags.all()]
        except Exception:
            pass
    # Try reverse from generic name
    if not tags and hasattr(f, "compliancetag_set"):
        try:
            tags = [t.slug if hasattr(t, "slug") else getattr(t, "name", str(t)) for t in f.compliancetag_set.all()]
        except Exception:
            pass

    compliance_joined = ",".join(sorted(set(tags)))

    # Plugin key if present in metadata
    plugin_key = ""
    if isinstance(f.metadata, dict):
        plugin_key = f.metadata.get("plugin_key") or f.metadata.get("plugin") or ""

    return [
        str(f.id),
        f.title or "",
        f.severity or "",
        category,
        url_or_file,
        param,
        f.first_seen_at.isoformat() if f.first_seen_at else "",
        f.last_seen_at.isoformat() if f.last_seen_at else "",
        f.status or "",
        compliance_joined,
        plugin_key,
        str(getattr(f.scan, "id", "")) if getattr(f, "scan_id", None) else "",
        str(getattr(f.target, "id", "")) if getattr(f, "target_id", None) else "",
    ]


def write_findings_csv_to_temp(qs: QuerySet, header: Optional[List[str]] = None) -> Tuple[str, int]:
    """
    Stream-like write of CSV to a NamedTemporaryFile (delete=False) and return (temp_path, rows_written).
    """
    if header is None:
        header = [
            "id",
            "title",
            "severity",
            "category",
            "url_or_file",
            "param",
            "first_seen",
            "last_seen",
            "status",
            "compliance_tags",
            "plugin_key",
            "scan_id",
            "target_id",
        ]

    tmp = tempfile.NamedTemporaryFile("w", newline="", delete=False, suffix=".csv", encoding="utf-8")
    writer = csv.writer(tmp)
    writer.writerow(header)
    count = 0
    # Iterate efficiently
    for f in qs.iterator(chunk_size=1000):
        writer.writerow(finding_to_csv_row(f))
        count += 1
    tmp.flush()
    tmp.close()
    return tmp.name, count


def move_temp_to_reports_storage(temp_path: str, final_name: Optional[str] = None) -> str:
    """
    Move a temp file into reports storage dir with desired name; return final absolute path.
    """
    storage_dir = ensure_reports_storage_dir()
    if not final_name:
        base = os.path.basename(temp_path)
        final_name = base
    final_path = os.path.join(storage_dir, final_name)
    # Ensure parent exists
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    shutil.move(temp_path, final_path)
    return final_path


def render_report_html(template: str, context: dict) -> str:
    """
    Render HTML using Django templates; template is relative like 'reports/pdf/scan_report.html'
    """
    return render_to_string(template, context)