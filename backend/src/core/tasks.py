from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from celery import shared_task
from celery import chain

from django.conf import settings
from django.utils import timezone as dj_timezone

# Import scanner registry and adapters (placeholders only; no real scanning)
from scanners import registry  # triggers adapter registration via scanners.__init__
from scanners.base import ScanContext, FindingRecord
from scanners.constants import Severity

from .models import ScanRun, Asset, ScanProfile

logger = logging.getLogger(__name__)


def _get_profile_enabled_scanners(profile: ScanProfile) -> List[str]:
    enabled = profile.enabled_scanners or []
    # Normalize to list of strings
    if isinstance(enabled, dict):
        # allow {"static": true} style; flatten keys with truthy values
        enabled = [k for (k, v) in enabled.items() if v]
    if not isinstance(enabled, list):
        enabled = []
    # Normalize and lower-case
    normalized = [str(x).strip() for x in enabled]
    return normalized


@shared_task
def prepare_scan(scan_run_id: int) -> List[str]:
    """
    Select adapters to run for this scan. Placeholder logic using profile.enabled_scanners.
    Returns a list of adapter names.
    """
    run = ScanRun.objects.select_related("asset", "profile").get(pk=scan_run_id)
    run.status = "running"
    run.started_at = dj_timezone.now()
    run.save(update_fields=["status", "started_at"])

    asset = {
        "id": run.asset_id,
        "name": run.asset.name,
        "type": run.asset.type,
        "url_or_cidr": run.asset.url_or_cidr,
    }
    profile = {
        "id": run.profile_id,
        "name": run.profile.name,
        "enabled_scanners": _get_profile_enabled_scanners(run.profile),
    }

    adapters = registry.get_all()
    enabled_list = profile["enabled_scanners"]
    enabled_set = set(enabled_list)

    # Type-level includes
    include_static_all = "static" in enabled_set
    include_dynamic_all = "dynamic" in enabled_set
    include_network_all = "network" in enabled_set

    selected: List[str] = []
    for a in adapters:
        try:
            # Explicit by name
            if a.name in enabled_set:
                selected.append(a.name)
                continue
            # By type buckets
            if a.type in enabled_set:
                selected.append(a.name)
                continue
            # Legacy static include
            if include_static_all and a.type == "static":
                selected.append(a.name)
                continue
            # New type-level includes for dynamic/network
            if include_dynamic_all and a.type == "dynamic":
                selected.append(a.name)
                continue
            if include_network_all and a.type == "network":
                selected.append(a.name)
                continue
            # Adapter self-support
            if a.supports(asset, profile):
                selected.append(a.name)
        except Exception as e:  # pragma: no cover
            logger.warning("Adapter %s.supports raised: %s", a.name, e)

    # Deduplicate while preserving order
    seen = set()
    selected = [x for x in selected if not (x in seen or seen.add(x))]

    # Fallback: if nothing selected, run all as a demo (safe since they are placeholders)
    if not selected:
        selected = [a.name for a in adapters]

    logger.info("prepare_scan(%s) selected adapters: %s", scan_run_id, selected)
    return selected


def _ensure_reports_dir() -> Path:
    base = Path("/app/var/reports")
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # pragma: no cover
        logger.error("Failed to create reports directory: %s", e)
    return base


@shared_task
def run_scanner(adapter_name: str, scan_run_id: int) -> List[Dict[str, Any]]:
    """
    Execute a single adapter and return list of finding dicts (primitive types).
    """
    run = ScanRun.objects.select_related("asset", "profile").get(pk=scan_run_id)
    adapter = registry.get_by_name(adapter_name)
    if not adapter:
        logger.warning("Adapter '%s' not found; skipping.", adapter_name)
        return []

    ctx = ScanContext(
        scan_run_id=scan_run_id,
        asset_id=run.asset_id,
        profile_id=run.profile_id,
        started_at=dj_timezone.now(),
        config=(run.meta or {}).get("config", {}),
        limits=(run.meta or {}).get("limits", {}),
    )
    try:
        adapter.validate_config(ctx)
    except Exception as e:
        logger.warning("Adapter %s config invalid: %s", adapter_name, e)
        return []

    findings: List[FindingRecord] = []
    try:
        findings = adapter.run(ctx) or []
    except Exception as e:  # pragma: no cover
        logger.exception("Adapter %s.run failed: %s", adapter_name, e)
        return []

    # Serialize dataclasses to primitives
    out = [f.to_primitive() if hasattr(f, "to_primitive") else asdict(f) for f in findings]
    logger.info("run_scanner(%s, %s) produced %d findings", scan_run_id, adapter_name, len(out))
    return out


@shared_task
def aggregate_results(scan_run_id: int, results_list: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Merge lists of findings and compute counts by severity and by category.
    Store under ScanRun.meta.aggregate = {"by_severity": {...}, "by_category": {...}, "total": int}
    """
    merged: List[Dict[str, Any]] = []
    for sub in results_list or []:
        merged.extend(sub or [])

    by_severity: Dict[str, int] = {s: 0 for s in Severity.ORDER}
    by_category: Dict[str, int] = {}

    for f in merged:
        sev = (f or {}).get("severity", Severity.INFO)
        cat = (f or {}).get("category", "uncategorized")
        if sev not in by_severity:
            by_severity[sev] = 0
        by_severity[sev] += 1
        by_category[cat] = by_category.get(cat, 0) + 1

    # Save in run.meta
    run = ScanRun.objects.get(pk=scan_run_id)
    meta = run.meta or {}
    meta["aggregate"] = {"by_severity": by_severity, "by_category": by_category, "total": len(merged)}
    # TODO: persist individual findings in a later subtask
    run.meta = meta
    run.save(update_fields=["meta"])

    logger.info(
        "aggregate_results(%s) by_severity=%s by_category=%s total=%d",
        scan_run_id,
        by_severity,
        by_category,
        len(merged),
    )
    return {"by_severity": by_severity, "by_category": by_category, "total": len(merged)}


@shared_task
def generate_report(scan_run_id: int) -> str:
    """
    Write a simple text report with aggregates + listing of findings to /app/var/reports/scan_{id}.txt
    Returns path.
    """
    run = ScanRun.objects.get(pk=scan_run_id)
    aggregate = (run.meta or {}).get("aggregate") or {}
    by_sev = aggregate.get("by_severity") or {}
    reports_dir = _ensure_reports_dir()
    report_path = reports_dir / f"scan_{scan_run_id}.txt"

    lines = ["Security Scanner Report", f"ScanRun: {scan_run_id}", ""]

    # Severity counts
    lines.append("Counts by severity:")
    for sev in Severity.ORDER:
        lines.append(f"  {sev}: {by_sev.get(sev, 0)}")

    # In absence of persisted findings, include a placeholder human-readable section.
    # When persistence is added, this section will iterate stored findings.
    lines.append("")
    lines.append("Findings (title and category):")
    # We cannot rely on persisted findings yet; try to include last-run in-memory snapshot if stored in meta
    findings = (run.meta or {}).get("last_results") or []
    if not findings:
        lines.append("  (no detailed findings persisted yet)")
    else:
        for f in findings:
            title = (f or {}).get("title", "untitled")
            category = (f or {}).get("category", "uncategorized")
            adapter_name = (f or {}).get("scanner_type", "unknown")
            # Prefix title with [adapter] for traceability
            prefixed = f"[{adapter_name}] {title}" if not title.startswith("[") else title
            lines.append(f"  - {prefixed}  category: {category}")

    content = "\n".join(lines) + "\n"
    try:
        report_path.write_text(content, encoding="utf-8")
    except Exception as e:  # pragma: no cover
        logger.error("Failed to write report file %s: %s", report_path, e)
        return str(report_path)

    # Update run meta with report path
    meta = run.meta or {}
    meta["report_path"] = str(report_path)
    run.meta = meta
    run.save(update_fields=["meta"])

    logger.info("generate_report(%s) -> %s", scan_run_id, report_path)
    return str(report_path)


@shared_task
def notify(scan_run_id: int) -> str:
    """
    Placeholder notification task.
    """
    run = ScanRun.objects.get(pk=scan_run_id)
    run.status = "completed"
    run.ended_at = dj_timezone.now()
    run.save(update_fields=["status", "ended_at"])
    msg = f"Scan {scan_run_id} completed"
    logger.info("notify(%s): %s", scan_run_id, msg)
    return msg


@shared_task
def orchestrate_scan(scan_run_id: int) -> str:
    """
    Orchestrate a scan using a sequential chain for reliability in this scaffold.

    Future enhancement: Use a chord:
      prepare_scan.s(scan_run_id) | group(run_scanner.s(name, scan_run_id) for name in ...) \
      | aggregate_results.s(scan_run_id) | generate_report.s(scan_run_id) | notify.s(scan_run_id)
    """
    # Step 1: select adapters
    selected = prepare_scan.apply(args=[scan_run_id]).get()  # list[str]

    # Step 2: run each scanner sequentially and collect results
    results: List[List[Dict[str, Any]]] = []
    flat: List[Dict[str, Any]] = []
    for name in selected:
        r = run_scanner.apply(args=[name, scan_run_id]).get()
        results.append(r)
        flat.extend(r or [])

    # Save last_results snapshot in meta so report can include titles/categories
    try:
        run = ScanRun.objects.get(pk=scan_run_id)
        meta = run.meta or {}
        meta["last_results"] = flat
        run.meta = meta
        run.save(update_fields=["meta"])
    except Exception:  # pragma: no cover
        pass

    # Step 3: aggregate
    _ = aggregate_results.apply(args=[scan_run_id, results]).get()

    # Step 4: generate report
    _ = generate_report.apply(args=[scan_run_id]).get()

    # Step 5: notify (also marks run completed)
    final_msg = notify.apply(args=[scan_run_id]).get()
    return final_msg