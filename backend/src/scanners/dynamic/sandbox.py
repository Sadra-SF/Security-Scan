from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Any
from urllib.parse import urlparse


@dataclass
class SandboxProfile:
    network_allow_domains: List[str] = field(default_factory=list)
    max_rps: int = 2
    max_runtime_s: int = 60


def validate_sandbox(target: Any) -> SandboxProfile:
    """
    Build a conservative sandbox profile for a target.
    - Allow only the target's hostname.
    - Limit to 2 rps and 60 seconds runtime.
    """
    addr = getattr(target, "address", "") or ""
    host = ""
    try:
        p = urlparse(addr)
        host = p.hostname or ""
    except Exception:
        host = ""
    allow = [host] if host else []
    return SandboxProfile(network_allow_domains=allow, max_rps=2, max_runtime_s=60)