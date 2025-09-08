from __future__ import annotations

import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from zapv2 import ZAPv2

from ..base import ScannerAdapter, ScanContext, debug_synthetic_finding, is_debug
from ..constants import ScannerType, Severity
from .. import registry
from ..types import FindingRecord, EvidenceItem

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
        evidence = EvidenceItem(
            kind="config_error",
            inline=f"ZAP configuration error: {reason}",
            content_type="text/plain",
            metadata={"reason": reason}
        )
        return FindingRecord(
            plugin_key=self.key,
            category="configuration",
            title="[dynamic.zap] invalid configuration",
            severity="low",
            description=f"ZAP placeholder config invalid: {reason}. This is a non-fatal warning; returning no findings.",
            evidence=[evidence],
            metadata={"owasp_tag": "A05:2021"},
            compliance_tags=["OWASP-A05:2021"]
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
                "Informational": "info",
                "Low": "low",
                "Medium": "medium",
                "High": "high"
            }
            severity = severity_map.get(alert.get("risk", "Low"), "low")

            evidence = EvidenceItem(
                kind="zap_alert",
                inline=alert.get("evidence", ""),
                content_type="text/plain",
                metadata={
                    "plugin_id": alert.get("pluginId", ""),
                    "cwe_id": alert.get("cweid", ""),
                    "wasc_id": alert.get("wascid", ""),
                    "alert_ref": alert.get("alertRef", ""),
                    "confidence": alert.get("confidence", "")
                }
            )

            finding = FindingRecord(
                plugin_key=self.key,
                category=alert.get("alert", "").lower().replace(" ", "_"),
                title=f"ZAP: {alert.get('alert', 'Unknown')}",
                severity=severity,
                description=alert.get("description", ""),
                location=alert.get("url", url),
                evidence=[evidence],
                metadata={
                    "owasp_tag": "A03:2021",
                    "zap_plugin_id": alert.get("pluginId", ""),
                    "zap_cwe": alert.get("cweid", ""),
                    "zap_wasc": alert.get("wascid", "")
                },
                compliance_tags=["OWASP-A03:2021"]
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
            return [self._invalid_config_finding("missing 'url'")]
        
        findings: List[FindingRecord] = []

        try:
            # Start ZAP if needed
            if not self._start_zap_daemon(zap_path, zap_host, zap_port):
                evidence = EvidenceItem(
                    kind="zap_startup_error",
                    inline="Failed to start ZAP daemon",
                    content_type="text/plain",
                    metadata={"zap_path": zap_path, "host": zap_host, "port": zap_port}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="configuration",
                    title="ZAP daemon failed to start",
                    severity="high",
                    description="Unable to start OWASP ZAP daemon for scanning.",
                    evidence=[evidence],
                    metadata={"owasp_tag": "A05:2021"},
                    compliance_tags=["OWASP-A05:2021"]
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
            elif mode == "api":
                # Run API scan
                zap.openapi.import_url(url)
                zap.ascan.scan(url)
                while int(zap.ascan.status()) < 100:
                    time.sleep(5)
                alerts = zap.core.alerts(baseurl=url)
            else:
                evidence = EvidenceItem(
                    kind="config_error",
                    inline=f"Unknown scan mode: {mode}",
                    content_type="text/plain",
                    metadata={"provided_mode": mode, "supported_modes": ["baseline", "active", "api"]}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="configuration",
                    title="Unknown ZAP scan mode",
                    severity="low",
                    description=f"Mode '{mode}' not supported. Use 'baseline', 'active', or 'api'.",
                    evidence=[evidence],
                    metadata={"owasp_tag": "A05:2021"},
                    compliance_tags=["OWASP-A05:2021"]
                ))
                return findings

            # Parse alerts
            findings.extend(self._parse_zap_alerts(alerts, url))

        except Exception as e:
            logger.error(f"ZAP scan failed: {e}")
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"ZAP scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "url": url, "mode": mode}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="ZAP scan error",
                severity="medium",
                description=f"Error during ZAP scan: {str(e)}",
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
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