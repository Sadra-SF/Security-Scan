from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.utils import timezone

from findings.models import Finding
from scanners.types import FindingRecord
from targets.models import Target
from scans.models import Scan

logger = logging.getLogger(__name__)


def _normalize_location(location: Optional[str]) -> str:
    if not location:
        return ""
    return location.strip().lower()


def compute_dedupe_hash(
    target_id: str,
    plugin_key: str,
    category: str,
    normalized_location: str,
    signature_dict: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute deterministic SHA256 hex across stable keys for deduplication within a target.
    """
    payload = {
        "t": str(target_id),
        "p": plugin_key,
        "c": category,
        "l": normalized_location,
        "s": signature_dict or {},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def severity_score(
    severity_enum: str,
    likelihood: float = 0.5,
    impact: float = 0.5,
    context_weight: float = 1.0,
) -> float:
    """
    CVSS-inspired very light bucketing. Values 0.0 - 10.0
    """
    base_map = {
        "info": 0.0,
        "low": 2.5,
        "medium": 5.0,
        "high": 7.5,
        "critical": 9.5,
    }
    base = base_map.get((severity_enum or "").lower(), 0.0)
    # clamp inputs
    likelihood = max(0.0, min(1.0, likelihood))
    impact = max(0.0, min(1.0, impact))
    context_weight = max(0.1, min(2.0, context_weight))
    derived = (likelihood * 0.5 + impact * 0.5) * 10.0
    score = (base * 0.6 + derived * 0.4) * context_weight
    return round(min(10.0, max(0.0, score)), 1)


def upsert_finding(scan: Scan, target: Target, record: FindingRecord) -> Finding:
    """
    Create or update a Finding for this target based on dedupe hash.
    - Maintains last_seen_at, locations list, metadata merge.
    - Updates cvss_score from severity_score if absent on model.
    """
    normalized_location = _normalize_location(record.location)
    dedupe = compute_dedupe_hash(
        target_id=str(target.id),
        plugin_key=record.plugin_key,
        category=record.category,
        normalized_location=normalized_location,
        signature_dict={"title": record.title},
    )
    now = timezone.now()

    defaults = {
        "scan": scan,
        "title": record.title,
        "description": record.description or "",
        "severity": record.severity.lower(),
        "cvss_score": Decimal(str(severity_score(record.severity))),
        "locations": [normalized_location] if normalized_location else [],
        "metadata": {
            "plugin_key": record.plugin_key,
            "category": record.category,
            **(record.metadata or {}),
        },
        "last_seen_at": now,
    }

    obj, created = Finding.objects.get_or_create(
        target=target,
        dedupe_hash=dedupe,
        defaults=defaults,
    )
    if not created:
        # update minimal fields
        changed = False
        if obj.severity != defaults["severity"]:
            obj.severity = defaults["severity"]
            changed = True
        # merge location
        if normalized_location:
            locs = set(obj.locations or [])
            if normalized_location not in locs:
                locs.add(normalized_location)
                obj.locations = sorted(list(locs))
                changed = True
        # merge metadata shallow
        meta = obj.metadata or {}
        meta.update(defaults["metadata"])
        obj.metadata = meta
        obj.last_seen_at = now
        obj.scan = scan or obj.scan
        # set score if missing
        if not obj.cvss_score:
            obj.cvss_score = defaults["cvss_score"]
        if changed:
            obj.save(update_fields=["severity", "locations", "metadata", "last_seen_at", "scan", "cvss_score", "updated_at"])
        else:
            obj.save(update_fields=["last_seen_at", "scan", "updated_at"])
    else:
        logger.info("Created finding %s for target=%s plugin=%s", obj.id, target.id, record.plugin_key)

    # compliance_tags are strings here; no M2M defined yet in models; store in metadata
    if getattr(record, "compliance_tags", None):
        meta = obj.metadata or {}
        meta.setdefault("compliance_tags", [])
        # merge unique
        merged = list({*(meta["compliance_tags"]), *record.compliance_tags})
        meta["compliance_tags"] = merged
        obj.metadata = meta
        obj.save(update_fields=["metadata", "updated_at"])

    return obj