from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod

from .constants import ScannerType, Severity


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


@dataclass(slots=True)
class FindingRecord:
    """Normalized finding representation across scanners."""
    scanner_type: str
    category: str
    title: str
    severity: str = Severity.INFO
    cvss: Optional[float] = None
    owasp_tag: Optional[str] = None
    gdpr_tag: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    evidence_summary: Optional[str] = None
    remediation: Optional[str] = None
    dedup_hash: Optional[str] = None

    def to_primitive(self) -> Dict[str, Any]:
        return asdict(self)


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

    @abstractmethod
    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        """Return True if this adapter should run for given asset/profile."""
        raise NotImplementedError


def debug_synthetic_finding(
    scanner_type: str,
    title: str,
    severity: str = Severity.LOW,
    category: str = "synthetic/demo",
) -> FindingRecord:
    """Helper to emit a synthetic finding when DJANGO_DEBUG=true."""
    return FindingRecord(
        scanner_type=scanner_type,
        category=category,
        title=title,
        severity=severity,
        description="Synthetic finding emitted in DEBUG mode for orchestration demo.",
        location=None,
        evidence_summary="N/A",
        remediation="N/A",
        dedup_hash=str(uuid.uuid4()),
    )


def is_debug() -> bool:
    return os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes", "on")