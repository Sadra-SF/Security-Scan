from __future__ import annotations

import logging
from typing import Iterable, List, Tuple

from django.utils import timezone

from scans.models import Scan
from scanners.registry import list_plugins_by_type, list_plugins
from targets.models import Target

logger = logging.getLogger(__name__)


def plan_scan(scan: Scan) -> List[str]:
    """
    Return plugin keys based on scan.type and available registry.
    We map Scan.type to plugin 'type':
      - manual/scheduled/active -> include both static and dynamic for now
      - passive -> static only
    """
    mode = (scan.type or "").lower()
    selected: List[str] = []
    if mode in ("passive",):
        for p in list_plugins_by_type("static"):
            selected.append(p.key)
    elif mode in ("active", "manual", "scheduled"):
        for p in list_plugins():
            if getattr(p, "type", None) in ("static", "dynamic"):
                selected.append(p.key)
    else:
        # fallback: run static only
        for p in list_plugins_by_type("static"):
            selected.append(p.key)

    # de-duplicate preserving order
    seen = set()
    selected = [k for k in selected if not (k in seen or seen.add(k))]
    return selected


def update_scan_status(
    scan: Scan,
    status: str,
    started_at: bool | None = None,
    finished_at: bool | None = None,
) -> Scan:
    """
    Update scan status timestamps conveniently.
    started_at/finished_at arguments: if True, set now; if False/None, don't change.
    """
    fields = ["status", "updated_at"]
    scan.status = status
    now = timezone.now()
    if started_at is True and not scan.started_at:
        scan.started_at = now
        fields.append("started_at")
    if finished_at is True:
        scan.finished_at = now
        fields.append("finished_at")
    scan.save(update_fields=fields)
    return scan


def enqueue_plugin_tasks(scan: Scan, plugins: Iterable[str]) -> Tuple[List[str], List[str]]:
    """
    Returns two lists: (static_plugin_keys, dynamic_plugin_keys)
    The Celery enqueuing is performed in scans.tasks.start_scan to keep celery import local.
    """
    static_keys: List[str] = []
    dynamic_keys: List[str] = []
    for key in plugins:
        # Lookup type from registry
        try:
            from scanners.registry import get_plugin
            plugin = get_plugin(key)
            if not plugin:
                logger.warning("Plugin %s not found; skipping", key)
                continue
            if getattr(plugin, "type", None) == "static":
                static_keys.append(key)
            elif getattr(plugin, "type", None) == "dynamic":
                dynamic_keys.append(key)
            else:
                # Unknown type; default static
                static_keys.append(key)
        except Exception as e:
            logger.exception("Failed to classify plugin %s: %s", key, e)
    return static_keys, dynamic_keys