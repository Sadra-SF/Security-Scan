from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import ScannerAdapter, ScanContext, FindingRecord, is_debug
from ..constants import ScannerType, Severity
from .. import registry


def _get_config_section(ctx: ScanContext) -> Dict[str, Any]:
    cfg = ctx.config or {}
    return cfg.get("nmap") or cfg.get("network", {}).get("nmap") or {}


class NetworkNmapAdapter(ScannerAdapter):
    # Registry identity
    key = "network_nmap"
    display_name = "Network Nmap Scanner"
    version = "1.0.0"

    @property
    def name(self) -> str:
        return "network.nmap"

    @property
    def type(self) -> str:
        return ScannerType.NETWORK

    def validate_config(self, ctx: ScanContext) -> None:
        # Placeholder validation; ensure types if present
        cfg = _get_config_section(ctx)
        if not isinstance(cfg, dict):
            return
        timing = cfg.get("timing")
        if timing and not str(timing).upper().startswith("T"):
            return

    def _invalid_config_finding(self, reason: str) -> FindingRecord:
        return FindingRecord(
            scanner_type=self.type,
            category="configuration",
            title="[network.nmap] invalid configuration",
            severity=Severity.LOW,
            description=f"nmap placeholder config invalid: {reason}. Non-fatal; returning no findings.",
            remediation="Provide 'targets' as a list of IP/CIDR or ensure Asset has url_or_cidr for defaults.",
        )

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx) or {}
        targets = cfg.get("targets")
        if not targets:
            # Read from run context meta via ScanRun asset (not available here), rely on limits/config fallback:
            # The orchestration passes only ctx; we cannot access Asset directly here.
            # Spec: if no targets and asset is network type with url_or_cidr present, use that as default.
            # We can't read asset here, so we depend on ctx.config.asset stashed by orchestrator later.
            asset_info = (ctx.config or {}).get("asset") or {}
            if asset_info.get("type") in {"host", "network", "cidr", "ip"} and asset_info.get("url_or_cidr"):
                targets = [asset_info["url_or_cidr"]]
        if not targets:
            if is_debug():
                return [self._invalid_config_finding("missing 'targets' and no network asset default")]
            return []

        if not is_debug():
            return []

        # Emit one synthetic open port finding for 443/tcp on first target
        first = str(targets[0])
        finding = FindingRecord(
            scanner_type=self.type,
            category="open_port",
            title="[network.nmap] open port detected 443/tcp",
            severity=Severity.LOW,
            owasp_tag=None,
            description=f"Simulated open port on {first} in DEBUG mode.",
            remediation="Verify service exposure",
            location=f"{first}:443/tcp",
        )
        return [finding]

    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        enabled = (profile or {}).get("enabled_scanners", [])
        asset_type = (asset or {}).get("type")
        is_network = asset_type in {"host", "network", "cidr", "ip"}
        return is_network and (self.name in enabled or self.type in enabled)


# Duplicate-safe registration on import
_adapter_net = NetworkNmapAdapter()
_net_key = getattr(_adapter_net, "key", None)
if not _net_key:
    raise ValueError("NetworkNmapAdapter must define a unique 'key'")

_net_exists = None
if hasattr(registry, "get"):
    try:
        _net_exists = registry.get(_net_key)
    except Exception:
        _net_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _net_exists = registry._plugins.get(_net_key)  # type: ignore[attr-defined]
    except Exception:
        _net_exists = None

if not _net_exists:
    registry.register(_adapter_net)