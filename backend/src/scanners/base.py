from __future__ import annotations

import os
import uuid
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod

from .constants import ScannerType, Severity
from .types import FindingRecord as BaseFindingRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ScanContext:
    """Execution context passed to scanners."""
    scan_run_id: int
    asset_id: int
    profile_id: int
    started_at: datetime
    config: Dict[str, Any] = field(default_factory=dict)
    limits: Dict[str, Any] = field(default_factory=dict)

    def to_primitive(self) -> Dict[str, Any]:
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat()
        return d


# Use FindingRecord from types module
FindingRecord = BaseFindingRecord


class ScannerAdapter(ABC):
    """Abstract scanner adapter interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique adapter name (e.g., 'static.deps')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def type(self) -> str:
        """Scanner type: static|dynamic|network."""
        raise NotImplementedError

    @abstractmethod
    def validate_config(self, ctx: ScanContext) -> None:
        """Validate ctx.config and ctx.limits. Raise ValueError if invalid."""
        raise NotImplementedError

    @abstractmethod
    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        """Execute the scan synchronously and return findings."""
        raise NotImplementedError

    def _create_error_finding(self, error: Exception, location: str = "", category: str = "error") -> FindingRecord:
        """Helper method to create error findings with proper evidence."""
        from .types import EvidenceItem
        evidence = EvidenceItem(
            kind="scan_error",
            inline=f"Scan error: {str(error)}",
            content_type="text/plain",
            metadata={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "location": location
            }
        )
        return FindingRecord(
            plugin_key=getattr(self, "key", "unknown"),
            category=category,
            title="Scanner execution error",
            severity="medium",
            description=f"Error during scan execution: {str(error)}",
            location=location,
            evidence=[evidence],
            metadata={"owasp_tag": "A05:2021"},
            compliance_tags=["OWASP-A05:2021"]
        )

    def execute_scan(self, ctx: ScanContext) -> List[FindingRecord]:
        """Wrapper method that provides comprehensive error handling and logging."""
        scanner_name = getattr(self, "name", "unknown")
        logger.info(f"Starting scan execution for {scanner_name}")

        try:
            # Validate configuration
            self.validate_config(ctx)
            logger.debug(f"Configuration validated for {scanner_name}")

            # Execute the scan
            findings = self.run(ctx)
            logger.info(f"Scan completed for {scanner_name}, found {len(findings)} findings")

            return findings

        except Exception as e:
            logger.exception(f"Scan execution failed for {scanner_name}: {e}")
            error_finding = self._create_error_finding(e, getattr(ctx.config, "asset", {}).get("address", ""))
            return [error_finding]

    @abstractmethod
    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        """Return True if this adapter should run for given asset/profile."""
        raise NotImplementedError


def debug_synthetic_finding(
    plugin_key: str,
    title: str,
    severity: str = "low",
    category: str = "synthetic/demo",
) -> FindingRecord:
    """Helper to emit a synthetic finding when DJANGO_DEBUG=true."""
    from .types import EvidenceItem
    evidence = EvidenceItem(
        kind="synthetic",
        inline="Synthetic finding for testing",
        content_type="text/plain"
    )
    return FindingRecord(
        plugin_key=plugin_key,
        category=category,
        title=title,
        severity=severity,
        description="Synthetic finding emitted in DEBUG mode for orchestration demo.",
        location=None,
        evidence=[evidence],
        metadata={"synthetic": True},
    )


def is_debug() -> bool:
    return os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes", "on")