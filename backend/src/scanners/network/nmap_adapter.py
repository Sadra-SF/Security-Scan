from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import nmap

from ..base import ScannerAdapter, ScanContext, is_debug
from ..constants import ScannerType, Severity
from .. import registry
from ..types import FindingRecord, EvidenceItem

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
        evidence = EvidenceItem(
            kind="config_error",
            inline=f"Nmap configuration error: {reason}",
            content_type="text/plain",
            metadata={"reason": reason}
        )
        return FindingRecord(
            plugin_key=self.key,
            category="configuration",
            title="[network.nmap] invalid configuration",
            severity="low",
            description=f"nmap placeholder config invalid: {reason}. Non-fatal; returning no findings.",
            evidence=[evidence],
            metadata={"owasp_tag": "A05:2021"},
            compliance_tags=["OWASP-A05:2021"]
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

                    evidence = EvidenceItem(
                        kind="port_scan",
                        inline=f"Port {port}/{proto} is open, service: {service}",
                        content_type="text/plain",
                        metadata={
                            "port": port,
                            "protocol": proto,
                            "service": service,
                            "state": state,
                            "product": host[proto][port].get('product', ''),
                            "version": host[proto][port].get('version', '')
                        }
                    )
                    finding = FindingRecord(
                        plugin_key=self.key,
                        category="open_port",
                        title=f"Open port {port}/{proto} ({service})",
                        severity=severity.lower(),
                        description=f"Port {port} is open on {target}, running {service}",
                        location=f"{target}:{port}/{proto}",
                        evidence=[evidence],
                        metadata={"owasp_tag": "A05:2021"},
                        compliance_tags=["OWASP-A05:2021"]
                    )
                    findings.append(finding)

        # Check for OS detection
        if 'osmatch' in host and host['osmatch']:
            os_match = host['osmatch'][0]
            if os_match['accuracy'] > 80:
                evidence = EvidenceItem(
                    kind="os_detection",
                    inline=f"OS: {os_match['name']} (accuracy: {os_match['accuracy']}%)",
                    content_type="text/plain",
                    metadata={
                        "os_name": os_match['name'],
                        "accuracy": os_match['accuracy'],
                        "os_class": os_match.get('osclass', [])
                    }
                )
                finding = FindingRecord(
                    plugin_key=self.key,
                    category="os_detection",
                    title=f"OS Detected: {os_match['name']}",
                    severity="info",
                    description=f"Operating system detected: {os_match['name']} (accuracy: {os_match['accuracy']}%)",
                    location=target,
                    evidence=[evidence],
                    metadata={"owasp_tag": "A05:2021"},
                    compliance_tags=["OWASP-A05:2021"]
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
            return [self._invalid_config_finding("missing 'targets' and no network asset default")]
        
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
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"Nmap scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "targets": targets}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="Nmap scan error",
                severity="medium",
                description=f"Error during Nmap scan: {str(e)}",
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
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