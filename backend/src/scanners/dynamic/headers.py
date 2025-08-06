from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import requests

from scanners.registry import scanner_plugin
from scanners.types import ScanContext, FindingRecord

logger = logging.getLogger(__name__)


@scanner_plugin(key="dynamic.headers", type="dynamic", name="Dynamic Security Headers")
class DynamicHeadersPlugin:
    """
    Minimal dynamic plugin that performs a HEAD (fallback to GET) to target.address and checks common security headers.
    Exception-safe and low-impact (5s timeout, single request).
    """

    IMPORTANT = {
        "content-security-policy": ("medium", "Missing Content-Security-Policy"),
        "x-frame-options": ("low", "Missing X-Frame-Options"),
        "x-content-type-options": ("low", "Missing X-Content-Type-Options"),
        "strict-transport-security": ("medium", "Missing Strict-Transport-Security"),
    }

    def run(self, context: ScanContext) -> Iterable[FindingRecord]:
        target = context.target
        url = getattr(target, "address", None) or ""
        if not isinstance(url, str) or not url:
            return []

        headers: dict[str, str] = {}
        error_note: Optional[str] = None
        try:
            # Prefer HEAD to be lightweight; some servers may not support it — fallback to GET.
            resp = context.http_session.head(url, timeout=context.timeout_secs, allow_redirects=True)
            if resp.status_code >= 400 or not resp.headers:
                resp = context.http_session.get(url, timeout=context.timeout_secs, allow_redirects=True)
            headers = {k.lower(): v for k, v in (resp.headers or {}).items()}
        except Exception as e:
            error_note = f"request_error: {type(e).__name__}"
            logger.warning("dynamic.headers fetch failed scan_id=%s url=%s err=%s", getattr(context.scan, "id", None), url, e)

        findings: List[FindingRecord] = []
        scheme_is_https = url.lower().startswith("https")

        for h, (default_sev, title) in self.IMPORTANT.items():
            present = h in headers and bool(headers.get(h))
            if present:
                continue
            sev = default_sev
            if h == "strict-transport-security" and not scheme_is_https:
                sev = "info"
            desc_bits = [f"Header '{h}' not observed on {url}"]
            if error_note:
                desc_bits.append(f"(note: {error_note})")
            findings.append(
                FindingRecord(
                    plugin_key="dynamic.headers",
                    category="missing_header",
                    title=title,
                    description="; ".join(desc_bits),
                    severity=sev,
                    location=url,
                    metadata={"observed_headers": list(headers.keys())[:50], "category": "missing_header"},
                    compliance_tags=["OWASP-ASVS-14.3.1"] if h in ("content-security-policy",) else [],
                )
            )

        return findings