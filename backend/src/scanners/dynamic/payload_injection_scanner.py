from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

from ..base import ScannerAdapter, ScanContext
from ..constants import ScannerType, Severity
from .. import registry
from ..types import FindingRecord, EvidenceItem

logger = logging.getLogger(__name__)


def _get_config_section(ctx: ScanContext) -> Dict[str, Any]:
    cfg = ctx.config or {}
    return cfg.get("payload") or cfg.get("injection") or {}


class PayloadInjectionScanner(ScannerAdapter):
    # Registry identity
    key = "dynamic_payload_injection"
    display_name = "Custom Payload Injection Scanner"
    version = "1.0.0"

    # Common injection payloads
    SQLI_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users; --",
        "admin' --",
        "' OR 1=1 --",
    ]

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "'><script>alert('XSS')</script>",
    ]

    COMMAND_INJECTION_PAYLOADS = [
        "; ls -la",
        "| cat /etc/passwd",
        "`whoami`",
        "$(cat /etc/passwd)",
        "; rm -rf /",
    ]

    @property
    def name(self) -> str:
        return "dynamic.payload_injection"

    @property
    def type(self) -> str:
        return ScannerType.DYNAMIC

    def validate_config(self, ctx: ScanContext) -> None:
        cfg = _get_config_section(ctx)
        if not isinstance(cfg, dict):
            return

    def _inject_payloads_in_url(self, url: str, payloads: List[str], payload_type: str) -> List[FindingRecord]:
        findings = []

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if not query_params:
            return findings

        for param_name, param_values in query_params.items():
            for param_value in param_values:
                for payload in payloads:
                    # Inject payload into parameter
                    modified_params = query_params.copy()
                    modified_params[param_name] = [payload]

                    # Reconstruct URL with injected payload
                    modified_query = urlencode(modified_params, doseq=True)
                    injected_url = parsed._replace(query=modified_query).geturl()

                    # Check for potential vulnerability indicators in the injected payload
                    vulnerability_indicators = self._check_payload_indicators(payload, payload_type)

                    if vulnerability_indicators:
                        evidence = EvidenceItem(
                            kind="payload_injection",
                            inline=f"Injected {payload_type} payload in URL parameter '{param_name}': {payload}",
                            content_type="text/plain",
                            metadata={
                                "payload_type": payload_type,
                                "parameter": param_name,
                                "original_value": param_value,
                                "injected_payload": payload,
                                "injected_url": injected_url,
                                "indicators": vulnerability_indicators
                            }
                        )
                        findings.append(FindingRecord(
                            plugin_key=self.key,
                            category=f"injection.{payload_type.lower()}",
                            title=f"Potential {payload_type} vulnerability via URL parameter",
                            severity="medium",
                            description=f"URL parameter '{param_name}' may be vulnerable to {payload_type} injection",
                            location=injected_url,
                            evidence=[evidence],
                            metadata={"owasp_tag": "A03:2021"},
                            compliance_tags=["OWASP-A03:2021"]
                        ))

        return findings

    def _inject_payloads_in_form(self, url: str, form_data: Dict[str, Any], payloads: List[str], payload_type: str) -> List[FindingRecord]:
        findings = []

        for field_name, field_value in form_data.items():
            for payload in payloads:
                # Inject payload into form field
                modified_form = form_data.copy()
                modified_form[field_name] = payload

                # Check for potential vulnerability indicators
                vulnerability_indicators = self._check_payload_indicators(payload, payload_type)

                if vulnerability_indicators:
                    evidence = EvidenceItem(
                        kind="form_injection",
                        inline=f"Injected {payload_type} payload in form field '{field_name}': {payload}",
                        content_type="text/plain",
                        metadata={
                            "payload_type": payload_type,
                            "field": field_name,
                            "original_value": str(field_value),
                            "injected_payload": payload,
                            "indicators": vulnerability_indicators
                        }
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category=f"injection.{payload_type.lower()}",
                        title=f"Potential {payload_type} vulnerability via form field",
                        severity="medium",
                        description=f"Form field '{field_name}' may be vulnerable to {payload_type} injection",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A03:2021"},
                        compliance_tags=["OWASP-A03:2021"]
                    ))

        return findings

    def _check_payload_indicators(self, payload: str, payload_type: str) -> List[str]:
        """Check payload for vulnerability indicators."""
        indicators = []

        if payload_type == "SQLi":
            sqli_indicators = ["'", "\"", ";", "--", "/*", "*/", "union", "select", "or", "and", "drop"]
            for indicator in sqli_indicators:
                if indicator in payload.lower():
                    indicators.append(f"SQLi indicator: {indicator}")

        elif payload_type == "XSS":
            xss_indicators = ["<script", "javascript:", "onerror", "onload", "alert(", "document."]
            for indicator in xss_indicators:
                if indicator in payload.lower():
                    indicators.append(f"XSS indicator: {indicator}")

        elif payload_type == "Command":
            cmd_indicators = [";", "|", "`", "$(", "rm", "ls", "cat", "whoami"]
            for indicator in cmd_indicators:
                if indicator in payload.lower():
                    indicators.append(f"Command injection indicator: {indicator}")

        return indicators

    def _test_custom_payloads(self, url: str, custom_payloads: List[str]) -> List[FindingRecord]:
        findings = []

        for payload in custom_payloads:
            # Determine payload type based on content
            payload_type = self._classify_payload(payload)

            # Test payload in URL parameters
            url_findings = self._inject_payloads_in_url(url, [payload], payload_type)
            findings.extend(url_findings)

            # Test payload in simulated form data
            form_data = {"input": "test_value", "search": "test", "query": "test"}
            form_findings = self._inject_payloads_in_form(url, form_data, [payload], payload_type)
            findings.extend(form_findings)

        return findings

    def _classify_payload(self, payload: str) -> str:
        """Classify payload type based on its content."""
        payload_lower = payload.lower()

        if any(indicator in payload_lower for indicator in ["select", "union", "drop", "insert", "update", "delete", "'", "or 1=1"]):
            return "SQLi"
        elif any(indicator in payload_lower for indicator in ["<script", "javascript:", "onerror", "alert(", "document."]):
            return "XSS"
        elif any(indicator in payload_lower for indicator in [";", "|", "`", "$("]):
            return "Command"
        else:
            return "Unknown"

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        target_url = (ctx.config or {}).get("asset", {}).get("address", "")

        findings = []

        if not target_url:
            return findings

        try:
            # Get custom payloads from config
            custom_payloads = cfg.get("custom_payloads", [])

            # Test custom payloads if provided
            if custom_payloads:
                findings.extend(self._test_custom_payloads(target_url, custom_payloads))

            # Test default payloads
            else:
                # Test SQLi payloads
                findings.extend(self._inject_payloads_in_url(target_url, self.SQLI_PAYLOADS, "SQLi"))

                # Test XSS payloads
                findings.extend(self._inject_payloads_in_url(target_url, self.XSS_PAYLOADS, "XSS"))

                # Test command injection payloads
                findings.extend(self._inject_payloads_in_url(target_url, self.COMMAND_INJECTION_PAYLOADS, "Command"))

        except Exception as e:
            logger.error(f"Payload injection scan failed for {target_url}: {e}")
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"Payload injection scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "url": target_url}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="Payload injection scan error",
                severity="medium",
                description=f"Error during payload injection scan: {str(e)}",
                location=target_url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        enabled = (profile or {}).get("enabled_scanners", [])
        asset_type = (asset or {}).get("type")
        is_web = asset_type in {"web", "http", "url", "api"}
        return is_web and (self.name in enabled or self.type in enabled)


# Duplicate-safe registration on import
_adapter_payload = PayloadInjectionScanner()
_payload_key = getattr(_adapter_payload, "key", None)
if not _payload_key:
    raise ValueError("PayloadInjectionScanner must define a unique 'key'")

_payload_exists = None
if hasattr(registry, "get"):
    try:
        _payload_exists = registry.get(_payload_key)
    except Exception:
        _payload_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _payload_exists = registry._plugins.get(_payload_key)
    except Exception:
        _payload_exists = None

if not _payload_exists:
    registry.register(_adapter_payload)