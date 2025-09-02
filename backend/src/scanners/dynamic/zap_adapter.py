from __future__ import annotations

import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from zapv2 import ZAPv2

from ..base import ScannerAdapter, ScanContext, FindingRecord, debug_synthetic_finding, is_debug
from ..constants import ScannerType, Severity
from .. import registry

logger = logging.getLogger(__name__)


def _get_config_section(ctx: ScanContext) -> Dict[str, Any]:
    cfg = ctx.config or {}
    return cfg.get("zap") or cfg.get("dynamic", {}).get("zap") or {}


class DynamicZapAdapter(ScannerAdapter):
    # Registry identity
    key = "dynamic_zap"
    display_name = "Dynamic ZAP Scanner"
    version = "1.0.0"

    @property
    def name(self) -> str:
        return "dynamic.zap"

    @property
    def type(self) -> str:
        return ScannerType.DYNAMIC

    def validate_config(self, ctx: ScanContext) -> None:
        # Validate minimal keys if provided; do not raise for placeholders
        cfg = _get_config_section(ctx)
        # Accept missing keys; real integration will enforce later
        if not isinstance(cfg, dict):
            # Silently accept; run() will handle with warning finding in DEBUG
            return
        # Validate enum-ish
        mode = cfg.get("mode")
        if mode and mode not in {"baseline", "active"}:
            # non-fatal
            return

    def _invalid_config_finding(self, reason: str) -> FindingRecord:
        return FindingRecord(
            scanner_type=self.type,
            category="configuration",
            title="[dynamic.zap] invalid configuration",
            severity=Severity.LOW,
            description=f"ZAP placeholder config invalid: {reason}. This is a non-fatal warning; returning no findings.",
            remediation="Provide required keys such as 'url' and a valid 'mode' (baseline|active).",
        )

    def _start_zap_daemon(self, zap_path: str = "zap.sh", host: str = "127.0.0.1", port: int = 8080) -> bool:
        """Start ZAP daemon if not already running."""
        try:
            # Check if ZAP is already running
            zap = ZAPv2(apikey="", proxies={'http': f'http://{host}:{port}', 'https': f'http://{host}:{port}'})
            zap.core.version()
            logger.info("ZAP is already running")
            return True
        except Exception:
            logger.info("Starting ZAP daemon")
            try:
                subprocess.Popen([zap_path, "-daemon", "-host", host, "-port", str(port)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(10)  # Wait for ZAP to start
                return True
            except Exception as e:
                logger.error(f"Failed to start ZAP: {e}")
                return False

    def _parse_zap_alerts(self, alerts: List[Dict[str, Any]], url: str) -> List[FindingRecord]:
        """Parse ZAP alerts into FindingRecord objects."""
        findings = []
        for alert in alerts:
            severity_map = {
                "Informational": Severity.INFO,
                "Low": Severity.LOW,
                "Medium": Severity.MEDIUM,
                "High": Severity.HIGH
            }
            severity = severity_map.get(alert.get("risk", "Low"), Severity.LOW)

            finding = FindingRecord(
                scanner_type=self.type,
                category=alert.get("alert", "").lower().replace(" ", "_"),
                title=f"ZAP: {alert.get('alert', 'Unknown')}",
                severity=severity,
                description=alert.get("description", ""),
                location=alert.get("url", url),
                evidence_summary=alert.get("evidence", ""),
                remediation=alert.get("solution", ""),
                dedup_hash=f"zap_{alert.get('pluginId', '')}_{alert.get('url', '')}"
            )
            findings.append(finding)
        return findings

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        url = (cfg or {}).get("url")
        mode = (cfg or {}).get("mode") or "baseline"
        zap_host = (cfg or {}).get("zap_host", "127.0.0.1")
        zap_port = int((cfg or {}).get("zap_port", 8080))
        zap_path = (cfg or {}).get("zap_path", "zap.sh")

        if not url:
            if is_debug():
                return [self._invalid_config_finding("missing 'url'")]
            return []

        if not is_debug():
            return []

        findings: List[FindingRecord] = []

        try:
            # Start ZAP if needed
            if not self._start_zap_daemon(zap_path, zap_host, zap_port):
                findings.append(FindingRecord(
                    scanner_type=self.type,
                    category="configuration",
                    title="ZAP daemon failed to start",
                    severity=Severity.HIGH,
                    description="Unable to start OWASP ZAP daemon for scanning.",
                    remediation="Ensure ZAP is installed and zap.sh is in PATH, or provide correct zap_path."
                ))
                return findings

            # Connect to ZAP
            zap = ZAPv2(apikey="", proxies={'http': f'http://{zap_host}:{zap_port}', 'https': f'http://{zap_host}:{zap_port}'})

            # Clear previous session
            zap.core.new_session()

            # Access the target
            zap.urlopen(url)

            if mode == "baseline":
                # Run baseline scan
                zap.ascan.scan(url)
                while int(zap.ascan.status()) < 100:
                    time.sleep(5)
                alerts = zap.core.alerts(baseurl=url)
            elif mode == "active":
                # Run active scan
                zap.ascan.scan(url)
                while int(zap.ascan.status()) < 100:
                    time.sleep(5)
                alerts = zap.core.alerts(baseurl=url)
            else:
                findings.append(FindingRecord(
                    scanner_type=self.type,
                    category="configuration",
                    title="Unknown ZAP scan mode",
                    severity=Severity.LOW,
                    description=f"Mode '{mode}' not supported. Use 'baseline' or 'active'.",
                    remediation="Configure mode as 'baseline' or 'active'."
                ))
                return findings

            # Parse alerts
            findings.extend(self._parse_zap_alerts(alerts, url))

        except Exception as e:
            logger.error(f"ZAP scan failed: {e}")
            findings.append(FindingRecord(
                scanner_type=self.type,
                category="error",
                title="ZAP scan error",
                severity=Severity.MEDIUM,
                description=f"Error during ZAP scan: {str(e)}",
                remediation="Check ZAP configuration and target URL accessibility."
            ))

        return findings

    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        enabled = (profile or {}).get("enabled_scanners", [])
        asset_type = (asset or {}).get("type")
        is_url = asset_type in {"web", "http", "url"}
        return is_url and (self.name in enabled or self.type in enabled)


# Duplicate-safe registration on import
_adapter_dyn = DynamicZapAdapter()
_dyn_key = getattr(_adapter_dyn, "key", None)
if not _dyn_key:
    raise ValueError("DynamicZapAdapter must define a unique 'key'")

_dyn_exists = None
if hasattr(registry, "get"):
    try:
        _dyn_exists = registry.get(_dyn_key)
    except Exception:
        _dyn_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _dyn_exists = registry._plugins.get(_dyn_key)  # type: ignore[attr-defined]
    except Exception:
        _dyn_exists = None

if not _dyn_exists:
    registry.register(_adapter_dyn)