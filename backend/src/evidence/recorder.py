from __future__ import annotations

import hashlib
import logging
import os
from io import BytesIO
from typing import Any, Optional, Union

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from evidence.models import Evidence
from findings.models import Finding
from scanners.types import EvidenceItem

logger = logging.getLogger(__name__)


def _calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def _get_file_size(content: bytes) -> int:
    """Get file size from content."""
    return len(content)


def _store_file_content(evidence: Evidence, content: bytes, filename: str) -> None:
    """Store file content using Django's storage system."""
    try:
        # Create a ContentFile from the bytes
        content_file = ContentFile(content, name=filename)

        # Save the file using the model's FileField
        evidence.file.save(filename, content_file, save=False)

        # Update evidence metadata
        evidence.size = len(content)
        evidence.sha256 = _calculate_file_hash(content)

        logger.info("Stored file for evidence %s: %s (%d bytes)", evidence.id, filename, len(content))
    except Exception as e:
        logger.error("Failed to store file content for evidence %s: %s", evidence.id, e)
        raise


def record_evidence(finding: Finding, evidence_item: EvidenceItem) -> Evidence:
    """
    Persist an Evidence row for a finding from a lightweight EvidenceItem.
    Handles file storage, inline content, external URLs, and screenshot capture.
    """
    try:
        storage_url = evidence_item.storage_url or ""
        meta = dict(evidence_item.metadata or {})

        # Handle different evidence types
        file_content = None
        filename = None

        # Special handling for screenshot evidence
        if evidence_item.kind == "screenshot" and meta.get("capture_url"):
            # Capture screenshot using Selenium
            try:
                from .screenshot import capture_screenshot_evidence
                screenshot_evidence = capture_screenshot_evidence(
                    finding=finding,
                    url=meta["capture_url"],
                    browser=meta.get("browser", "chrome"),
                    headless=meta.get("headless", True),
                    wait_time=meta.get("wait_time", 5),
                    full_page=meta.get("full_page", False),
                    element_selector=meta.get("element_selector"),
                    title=meta.get("title"),
                    metadata={k: v for k, v in meta.items() if k not in ["capture_url", "browser", "headless", "wait_time", "full_page", "element_selector"]}
                )
                logger.info("Captured screenshot evidence %s for finding %s", screenshot_evidence.id, finding.id)
                return screenshot_evidence
            except Exception as e:
                logger.error("Screenshot capture failed: %s", e)
                # Fall back to creating evidence without screenshot
                meta["screenshot_error"] = str(e)

        if evidence_item.inline and not storage_url:
            # Store inline content as a file
            if isinstance(evidence_item.inline, str):
                file_content = evidence_item.inline.encode('utf-8')
                filename = f"{evidence_item.kind}_{finding.id}.txt"
            else:
                # For non-string inline content, store as JSON in metadata
                meta["inline"] = evidence_item.inline

        elif storage_url.startswith(('http://', 'https://')):
            # External URL - don't download, just store reference
            pass

        elif storage_url and os.path.exists(storage_url):
            # Local file path - read and store
            try:
                with open(storage_url, 'rb') as f:
                    file_content = f.read()
                filename = os.path.basename(storage_url)
            except Exception as e:
                logger.warning("Failed to read local file %s: %s", storage_url, e)
                # Fall back to storing the path as storage_url

        # Create the Evidence instance
        ev = Evidence.objects.create(
            finding=finding,
            kind=str(evidence_item.kind or "other"),
            storage_url=storage_url if not file_content else "",
            content_type=evidence_item.content_type or "",
            size=evidence_item.size,
            sha256=evidence_item.sha256 or "",
            metadata=meta,
        )

        # Store file content if we have it
        if file_content and filename:
            _store_file_content(ev, file_content, filename)
            ev.save(update_fields=['file', 'size', 'sha256'])

        # Add ID reference into Finding.evidence_refs list
        refs = list(finding.evidence_refs or [])
        refs.append(str(ev.id))
        finding.evidence_refs = refs
        finding.save(update_fields=["evidence_refs", "updated_at"])

        # Enrich evidence with additional metadata
        try:
            from .enrichment import EvidenceEnricher
            context = {
                'finding': finding,
                'evidence_type': evidence_item.kind,
            }
            EvidenceEnricher.enrich_evidence(ev, context)
        except ImportError:
            logger.debug("Evidence enrichment not available")
        except Exception as e:
            logger.warning(f"Evidence enrichment failed: {e}")

        logger.info("Recorded evidence %s for finding %s", ev.id, finding.id)
        return ev

    except Exception as e:
        logger.exception("record_evidence failed for finding=%s: %s", getattr(finding, "id", None), e)
        # Fail-safe: do not raise
        raise


def record_evidence_from_file(finding: Finding, file_path: str, kind: str = "artifact",
                           content_type: str = "", metadata: Optional[dict] = None) -> Evidence:
    """
    Convenience function to record evidence from a file path.
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        evidence_item = EvidenceItem(
            kind=kind,
            storage_url=file_path,
            content_type=content_type,
            size=len(content),
            sha256=_calculate_file_hash(content),
            metadata=metadata or {}
        )

        return record_evidence(finding, evidence_item)

    except Exception as e:
        logger.exception("record_evidence_from_file failed for %s: %s", file_path, e)
        raise


def record_evidence_from_content(finding: Finding, content: Union[str, bytes],
                               filename: str, kind: str = "artifact",
                               content_type: str = "", metadata: Optional[dict] = None) -> Evidence:
    """
    Convenience function to record evidence from content directly.
    """
    try:
        if isinstance(content, str):
            # For strings, use inline
            evidence_item = EvidenceItem(
                kind=kind,
                inline=content,
                content_type=content_type,
                size=len(content.encode('utf-8')),
                sha256=_calculate_file_hash(content.encode('utf-8')),
                metadata=metadata or {}
            )
        else:
            # For bytes, create evidence with file content directly
            content_bytes = content
            ev = Evidence.objects.create(
                finding=finding,
                kind=kind,
                content_type=content_type,
                size=len(content_bytes),
                sha256=_calculate_file_hash(content_bytes),
                metadata=metadata or {},
            )

            # Store the file content
            _store_file_content(ev, content_bytes, filename)
            ev.save(update_fields=['file', 'size', 'sha256'])

            # Add to finding refs
            refs = list(finding.evidence_refs or [])
            refs.append(str(ev.id))
            finding.evidence_refs = refs
            finding.save(update_fields=["evidence_refs", "updated_at"])

            # Enrich evidence with additional metadata
            try:
                from .enrichment import EvidenceEnricher
                context = {
                    'finding': finding,
                    'evidence_type': kind,
                    'content_type': content_type,
                }
                EvidenceEnricher.enrich_evidence(ev, context)
            except ImportError:
                logger.debug("Evidence enrichment not available")
            except Exception as e:
                logger.warning(f"Evidence enrichment failed: {e}")

            return ev

        return record_evidence(finding, evidence_item)

    except Exception as e:
        logger.exception("record_evidence_from_content failed: %s", e)
        raise