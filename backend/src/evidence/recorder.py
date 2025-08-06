from __future__ import annotations

import logging
from typing import Any, Optional

from evidence.models import Evidence
from findings.models import Finding
from scanners.types import EvidenceItem

logger = logging.getLogger(__name__)


def record_evidence(finding: Finding, evidence_item: EvidenceItem) -> Evidence:
    """
    Persist an Evidence row for a finding from a lightweight EvidenceItem.
    Safe and minimal; stores inline text as a small artifact if provided.
    """
    try:
        storage_url = evidence_item.storage_url or ""
        meta = dict(evidence_item.metadata or {})
        if evidence_item.inline and not storage_url:
            # For placeholder purposes, store inline text into metadata only, do not persist blob
            meta["inline"] = evidence_item.inline

        ev = Evidence.objects.create(
            finding=finding,
            kind=str(evidence_item.kind or "other"),
            storage_url=storage_url,
            content_type=evidence_item.content_type or "",
            size=evidence_item.size,
            sha256=evidence_item.sha256 or "",
            metadata=meta,
        )
        # Add ID reference into Finding.evidence_refs list
        refs = list(finding.evidence_refs or [])
        refs.append(str(ev.id))
        finding.evidence_refs = refs
        finding.save(update_fields=["evidence_refs", "updated_at"])
        return ev
    except Exception as e:
        logger.exception("record_evidence failed for finding=%s: %s", getattr(finding, "id", None), e)
        # Fail-safe: do not raise
        raise