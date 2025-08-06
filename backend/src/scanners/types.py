from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EvidenceItem:
    kind: str  # screenshot|log|request|response|artifact|other
    storage_url: Optional[str] = None
    inline: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    sha256: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanContext:
    target: Any  # targets.models.Target
    scan: Any  # scans.models.Scan
    http_session: Any = None  # requests.Session placeholder
    rate_limiter: Any = None
    evidence_recorder: Optional[Callable[[Any, EvidenceItem], Any]] = None
    user_agent: str = "SecurityScanner/0.1 (+https://example.invalid)"
    timeout_secs: int = 5


@dataclass
class FindingRecord:
    plugin_key: str
    category: str
    title: str
    description: str = ""
    severity: str = "info"  # info|low|medium|high|critical
    location: Optional[str] = None
    evidence: List[EvidenceItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    compliance_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        def serialize(obj):
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
            if isinstance(obj, list):
                return [serialize(x) for x in obj]
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            return obj

        return serialize(self)