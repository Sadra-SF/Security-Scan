from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import nmap

from ..base import ScannerAdapter, ScanContext, FindingRecord, is_debug
from ..constants import ScannerType, Severity
from .. import registry

logger = logging.getLogger(__name__)


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

    def _parse_nmap_results(self, nm: nmap.PortScanner, target: str) -> List[FindingRecord]:
        """Parse Nmap scan results into FindingRecord objects."""
        findings = []

        if target not in nm.all_hosts():
            return findings

        host = nm[target]

        # Check for open ports
        for proto in host.all_protocols():
            ports = host[proto].keys()
            for port in ports:
                state = host[proto][port]['state']
                service = host[proto][port]['name']
                if state == 'open':
                    severity = Severity.LOW
                    if port in [21, 23, 25, 53, 80, 110, 143, 443, 993, 995]:
                        severity = Severity.MEDIUM  # Common vulnerable services

                    finding = FindingRecord(
                        scanner_type=self.type,
                        category="open_port",
                        title=f"Open port {port}/{proto} ({service})",
                        severity=severity,
                        description=f"Port {port} is open on {target}, running {service}",
                        location=f"{target}:{port}/{proto}",
                        evidence_summary=f"Service: {service}, State: {state}",
                        remediation="Review if this port/service should be exposed. Consider firewall rules."
                    )
                    findings.append(finding)

        # Check for OS detection
        if 'osmatch' in host and host['osmatch']:
            os_match = host['osmatch'][0]
            if os_match['accuracy'] > 80:
                finding = FindingRecord(
                    scanner_type=self.type,
                    category="os_detection",
                    title=f"OS Detected: {os_match['name']}",
                    severity=Severity.INFO,
                    description=f"Operating system detected: {os_match['name']} (accuracy: {os_match['accuracy']}%)",
                    location=target,
                    evidence_summary=f"OS: {os_match['name']}"
                )
                findings.append(finding)

        return findings

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx) or {}
        targets = cfg.get("targets")
        scan_args = cfg.get("scan_args", "-sV -O")  # Version detection and OS detection

        if not targets:
            asset_info = (ctx.config or {}).get("asset") or {}
            if asset_info.get("type") in {"host", "network", "cidr", "ip"} and asset_info.get("url_or_cidr"):
                targets = [asset_info["url_or_cidr"]]
        if not targets:
            if is_debug():
                return [self._invalid_config_finding("missing 'targets' and no network asset default")]
            return []

        if not is_debug():
            return []

        findings: List[FindingRecord] = []

        try:
            nm = nmap.PortScanner()
            for target in targets:
                logger.info(f"Scanning {target} with args: {scan_args}")
                nm.scan(hosts=target, arguments=scan_args)
                target_findings = self._parse_nmap_results(nm, target)
                findings.extend(target_findings)

        except Exception as e:
            logger.error(f"Nmap scan failed: {e}")
            findings.append(FindingRecord(
                scanner_type=self.type,
                category="error",
                title="Nmap scan error",
                severity=Severity.MEDIUM,
                description=f"Error during Nmap scan: {str(e)}",
                remediation="Ensure nmap is installed and target is reachable."
            ))

        return findings

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