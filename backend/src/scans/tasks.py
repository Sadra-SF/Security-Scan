from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List, Optional

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from scans.models import Scan
from targets.models import Target
from scanners.registry import get_plugin, list_plugins, list_plugins_by_type
from scanners.types import ScanContext, FindingRecord
from scans.services import plan_scan, update_scan_status, enqueue_plugin_tasks
from findings.ingestion import upsert_finding
from evidence.recorder import record_evidence

logger = logging.getLogger(__name__)


def _mk_http_session(user_agent: str, timeout: int) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent})
    s.request = s.request  # keep reference for type checkers
    # We won't globally set timeouts; plugins must pass timeout in requests.* calls
    return s


def _build_context(scan: Scan, target: Target) -> ScanContext:
    defaults = getattr(settings, "SCANNER_DEFAULTS", {}) or {}
    ua = defaults.get("USER_AGENT", "SecurityScanner/0.1")
    timeout = int(defaults.get("HTTP_TIMEOUT_SECS", 5))
    session = _mk_http_session(ua, timeout)

    # Evidence recorder callback wiring
    def _recorder_cb(finding_model, evidence_item):
        from evidence.recorder import record_evidence as _rec_ev  # local import
        return _rec_ev(finding_model, evidence_item)

    # Optional: build sandbox profile for dynamic scans; plugins may inspect ctx.config
    try:
        from scanners.dynamic.sandbox import validate_sandbox
        sandbox_profile = validate_sandbox(target)
    except Exception:
        sandbox_profile = None

    ctx = ScanContext(
        target=target,
        scan=scan,
        http_session=session,
        rate_limiter=None,
        evidence_recorder=_recorder_cb,
        user_agent=ua,
        timeout_secs=timeout,
    )
    # stash sandbox profile in context.config-like area via metadata if present
    try:
        # ScanContext in scanners.types has no generic config; attach attribute dynamically
        setattr(ctx, "config", scan.config or {})
        setattr(ctx, "asset_id", str(target.id))
        setattr(ctx, "sandbox_profile", sandbox_profile)
    except Exception:
        pass
    return ctx


@shared_task(bind=True, name="scans.start_scan", soft_time_limit=60, time_limit=120, autoretry_for=(), retry_backoff=False)
def start_scan(self, scan_id: str) -> Dict[str, Any]:
    """
    Control task. Plans plugins and enqueues static/dynamic tasks.
    """
    scan = Scan.objects.select_related("target").get(pk=scan_id)
    target = scan.target

    update_scan_status(scan, Scan.Status.RUNNING, started_at=True)

    plugins = plan_scan(scan)
    static_keys, dynamic_keys = enqueue_plugin_tasks(scan, plugins)

    logger.info("start_scan scan_id=%s static=%s dynamic=%s", scan_id, static_keys, dynamic_keys)

    # For testing without Redis: run plugins synchronously
    try:
        # Try async first (if Redis available)
        for key in static_keys:
            run_static_scan.apply_async(args=[scan_id, key], queue="scans.static")
        for key in dynamic_keys:
            run_dynamic_scan.apply_async(args=[scan_id, key, None], queue="scans.dynamic")
        logger.info("Successfully enqueued plugin tasks asynchronously")
    except Exception as e:
        logger.warning("Async enqueue failed, running synchronously: %s", e)
        # Fallback to synchronous execution
        for key in static_keys:
            try:
                run_static_scan(scan_id, key)
                logger.info("Completed static scan for plugin %s", key)
            except Exception as plugin_e:
                logger.error("Failed static scan for plugin %s: %s", key, plugin_e)

        for key in dynamic_keys:
            try:
                run_dynamic_scan(scan_id, key, None)
                logger.info("Completed dynamic scan for plugin %s", key)
            except Exception as plugin_e:
                logger.error("Failed dynamic scan for plugin %s: %s", key, plugin_e)

    # Aggregation is manual for now; callers can enqueue aggregate_results later
    return {"static": static_keys, "dynamic": dynamic_keys}


@shared_task(bind=True, name="scans.run_static_scan", soft_time_limit=480, time_limit=600, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=120)
def run_static_scan(self, scan_id: str, plugin_key: str) -> Dict[str, Any]:
    """
    Execute a static plugin and ingest results.
    """
    scan = Scan.objects.select_related("target").get(pk=scan_id)
    target = scan.target
    plugin = get_plugin(plugin_key)
    if not plugin:
        logger.warning("run_static_scan unknown plugin %s", plugin_key)
        return {"count": 0, "errors": ["plugin_not_found"]}

    ctx = _build_context(scan, target)
    count = 0
    errors: List[str] = []
    try:
        findings: Iterable[FindingRecord] = plugin.run(ctx) or []
        for rec in findings:
            try:
                f = upsert_finding(scan, target, rec)
                # attach any evidence
                for ev in getattr(rec, "evidence", []) or []:
                    try:
                        record_evidence(f, ev)
                    except Exception as ee:
                        # tolerate evidence failure
                        logger.warning("record_evidence failed scan_id=%s plugin=%s finding=%s err=%s", scan_id, plugin_key, f.id, ee)
                count += 1
            except Exception as e:
                logger.exception("ingestion failure scan_id=%s plugin=%s: %s", scan_id, plugin_key, e)
                errors.append("ingestion_error")
    except Exception as e:
        logger.exception("plugin runtime error scan_id=%s plugin=%s: %s", scan_id, plugin_key, e)
        errors.append("plugin_error")

    return {"count": count, "errors": errors}


@shared_task(bind=True, name="scans.run_dynamic_scan", soft_time_limit=1500, time_limit=1800, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300)
def run_dynamic_scan(self, scan_id: str, plugin_key: str, sandbox_profile: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a dynamic plugin and ingest results.
    """
    scan = Scan.objects.select_related("target").get(pk=scan_id)
    target = scan.target
    plugin = get_plugin(plugin_key)
    if not plugin:
        logger.warning("run_dynamic_scan unknown plugin %s", plugin_key)
        return {"count": 0, "errors": ["plugin_not_found"]}

    ctx = _build_context(scan, target)
    count = 0
    errors: List[str] = []
    try:
        findings: Iterable[FindingRecord] = plugin.run(ctx) or []
        for rec in findings:
            try:
                f = upsert_finding(scan, target, rec)
                for ev in getattr(rec, "evidence", []) or []:
                    try:
                        record_evidence(f, ev)
                    except Exception as ee:
                        logger.warning("record_evidence failed scan_id=%s plugin=%s finding=%s err=%s", scan_id, plugin_key, f.id, ee)
                count += 1
            except Exception as e:
                logger.exception("ingestion failure scan_id=%s plugin=%s: %s", scan_id, plugin_key, e)
                errors.append("ingestion_error")
    except Exception as e:
        logger.exception("plugin runtime error scan_id=%s plugin=%s: %s", scan_id, plugin_key, e)
        errors.append("plugin_error")

    return {"count": count, "errors": errors}


@shared_task(bind=True, name="scans.aggregate_results", soft_time_limit=60, time_limit=120, autoretry_for=(), retry_backoff=False)
def aggregate_results(self, scan_id: str) -> Dict[str, Any]:
    """
    Aggregate counts by severity and categories for a scan and finalize status.
    Enqueue notifications for scan completion/failure and severity threshold if applicable.
    """
    scan = Scan.objects.select_related("target").get(pk=scan_id)
    # Pull findings for this scan's target; use scan linkage or last_seen within time window
    from findings.models import Finding  # local import to avoid circulars

    qs = Finding.objects.filter(target=scan.target)
    # If scan linkage present use that, else all for target
    linked = qs.filter(scan=scan)
    use_qs = linked if linked.exists() else qs

    by_severity: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    total = 0
    for f in use_qs:
        sev = (f.severity or "info").lower()
        by_severity[sev] = by_severity.get(sev, 0) + 1
        cat = (f.metadata or {}).get("category") or (f.title.split(":")[0] if ":" in f.title else "uncategorized")
        by_category[cat] = by_category.get(cat, 0) + 1
        total += 1

    scan.stats = {"by_severity": by_severity, "by_category": by_category, "total": total}
    # Finalize status optimistic to completed if not failed already
    if scan.status != Scan.Status.FAILED:
        scan.status = Scan.Status.COMPLETED
    scan.finished_at = timezone.now()
    scan.save(update_fields=["stats", "status", "finished_at", "updated_at"])

    # Enqueue notifications with synchronous fallback
    try:
        from notifications.tasks import dispatch_event  # local import to avoid circulars
        # Determine completion or failure
        evt = "scan.failed" if scan.status == Scan.Status.FAILED else "scan.completed"
        dispatch_event.apply_async(args=[evt, str(scan.id)], queue="notifications.send")

        # Threshold event: default High+
        defaults = getattr(settings, "NOTIFICATIONS_DEFAULTS", {}) or {}
        threshold = str(defaults.get("threshold_severity", "high")).lower()
        order = ["info", "low", "medium", "high", "critical"]
        try:
            idx = order.index(threshold)
        except ValueError:
            idx = order.index("high")
        has_threshold = any((by_severity.get(s, 0) or 0) > 0 for s in order[idx:])
        if has_threshold:
            dispatch_event.apply_async(args=["severity.threshold", str(scan.id)], queue="notifications.send")
    except Exception as e:
        logger.warning("aggregate_results async notification enqueue failed scan_id=%s err=%s, trying synchronous fallback", scan_id, e)
        # Synchronous fallback
        try:
            from notifications.tasks import dispatch_event_sync  # Import synchronous version
            evt = "scan.failed" if scan.status == Scan.Status.FAILED else "scan.completed"
            dispatch_event_sync(evt, str(scan.id))

            # Threshold event fallback
            defaults = getattr(settings, "NOTIFICATIONS_DEFAULTS", {}) or {}
            threshold = str(defaults.get("threshold_severity", "high")).lower()
            order = ["info", "low", "medium", "high", "critical"]
            try:
                idx = order.index(threshold)
            except ValueError:
                idx = order.index("high")
            has_threshold = any((by_severity.get(s, 0) or 0) > 0 for s in order[idx:])
            if has_threshold:
                dispatch_event_sync("severity.threshold", str(scan.id))

            logger.info("aggregate_results synchronous notification fallback succeeded scan_id=%s", scan_id)
        except Exception as sync_e:
            logger.error("aggregate_results synchronous notification fallback also failed scan_id=%s err=%s", scan_id, sync_e)

    return scan.stats