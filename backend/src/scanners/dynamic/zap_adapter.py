from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import ScannerAdapter, ScanContext, FindingRecord, debug_synthetic_finding, is_debug
from ..constants import ScannerType, Severity
from .. import registry


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

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        url = (cfg or {}).get("url")
        mode = (cfg or {}).get("mode") or "baseline"
        # Required key check (do not raise)
        if not url:
            # As per spec: return [] with a warning in FindingRecord description mentioning config invalid.
            # We include a single LOW-severity configuration finding only in DEBUG to avoid noisy output.
            if is_debug():
                return [self._invalid_config_finding("missing 'url'")]
            return []

        if not is_debug():
            # Dry-run/no-op when not in DEBUG
            return []

        findings: List[FindingRecord] = []

        # Synthetic outputs per mode
        if mode == "baseline":
            findings.append(
                FindingRecord(
                    scanner_type=self.type,
                    category="missing_header",
                    title="[dynamic.zap] ZAP baseline simulated missing security header",
                    severity=Severity.MEDIUM,
                    owasp_tag="A05:2021",
                    description=f"Baseline scan simulated for {url}. Indicates a missing security header in DEBUG mode.",
                    remediation="Ensure standard security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) are configured.",
                )
            )
        elif mode == "active":
            findings.append(
                FindingRecord(
                    scanner_type=self.type,
                    category="injection",
                    title="[dynamic.zap] ZAP active simulated SQLi",
                    severity=Severity.HIGH,
                    owasp_tag="A03:2021",
                    description=f"Active scan simulated for {url}. Indicates possible SQL injection in DEBUG mode.",
                    remediation="Parameterize queries and validate inputs server-side. Add WAF rules as defense-in-depth.",
                )
            )
        else:
            # Unknown mode, still emit a small note
            findings.append(
                debug_synthetic_finding(
                    scanner_type=self.type,
                    title="[dynamic.zap] ZAP simulated run (unknown mode)",
                    severity=Severity.LOW,
                    category="synthetic/demo",
                )
            )

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