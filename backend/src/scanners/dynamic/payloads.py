from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse, parse_qsl

from scanners.types import FindingRecord, EvidenceItem


@dataclass
class Page:
    url: str
    status: Optional[int]
    headers: Dict[str, str]
    elapsed_ms: Optional[int]
    body_excerpt: str


def _evidence_from_page(page: Page, extra_meta: Optional[Dict[str, str]] = None) -> EvidenceItem:
    subset_headers = {k: page.headers.get(k, "") for k in [
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
        "strict-transport-security",
    ] if k in page.headers}
    meta = {
        "url": page.url,
        "status": page.status,
        "elapsed_ms": page.elapsed_ms,
        "headers": subset_headers,
    }
    if extra_meta:
        meta.update(extra_meta)
    body_excerpt = (page.body_excerpt or "")[:500]
    return EvidenceItem(kind="response", inline=body_excerpt, content_type="text/html", metadata=meta)


def test_headers(page: Page) -> List[FindingRecord]:
    """
    Check for common security headers; return FindingRecord list.
    """
    findings: List[FindingRecord] = []
    hdrs = {k.lower(): v for k, v in (page.headers or {}).items()}

    checks = [
        ("strict-transport-security", "Missing HSTS header", "medium"),
        ("content-security-policy", "Missing Content-Security-Policy header", "medium"),
        ("x-frame-options", "Missing X-Frame-Options header", "low"),
        ("x-content-type-options", "Missing X-Content-Type-Options header", "low"),
        ("referrer-policy", "Missing Referrer-Policy header", "low"),
        ("permissions-policy", "Missing Permissions-Policy header", "low"),
    ]

    for key, title, severity in checks:
        present = key in hdrs and bool(hdrs.get(key))
        sev = severity
        if key == "strict-transport-security" and not page.url.lower().startswith("https"):
            # HSTS is HTTPS-only; downgrade if base URL not HTTPS
            sev = "info"
        if not present:
            findings.append(
                FindingRecord(
                    plugin_key="dynamic.crawler.headers",
                    category="missing_header",
                    title=title,
                    description=f"Header '{key}' not observed on {page.url}",
                    severity=sev,
                    location=page.url,
                    metadata={"category": "missing_header", "header": key},
                    compliance_tags=["A05:2021-Security Misconfiguration"],
                    evidence=[_evidence_from_page(page)],
                )
            )
    return findings


def test_xss_reflection(page: Page, token: str) -> List[FindingRecord]:
    """
    If token appears unescaped in body_excerpt, emit a potential XSS finding.
    """
    findings: List[FindingRecord] = []
    body = page.body_excerpt or ""
    if token and token in body:
        import json
        evidence_items = [_evidence_from_page(page, {"probe": json.dumps({"token": token})})]

        # Add screenshot evidence for visual confirmation
        try:
            from evidence.utils import create_screenshot_evidence
            screenshot_evidence = create_screenshot_evidence(
                url=page.url,
                title=f"XSS Reflection - {page.url}",
                wait_time=3,
                metadata={
                    "vulnerability_type": "xss_reflection",
                    "token": token,
                    "detection_method": "body_reflection"
                }
            )
            evidence_items.append(screenshot_evidence)
        except ImportError:
            # Screenshot functionality not available, continue without it
            pass

        findings.append(
            FindingRecord(
                plugin_key="dynamic.crawler.xss",
                category="xss.reflection",
                title="Reflected input detected in response body",
                description=f"A test token appears reflected in the response for {page.url}",
                severity="medium",
                location=page.url,
                metadata={"token": token},
                compliance_tags=["A03:2021-Injection/XSS"],
                evidence=evidence_items,
            )
        )
    return findings


def test_sqli_echo(page: Page, baseline_len: int) -> List[FindingRecord]:
    """
    Heuristic Length-based SQLi signal: only applicable if URL has exactly one query parameter.
    If body length deviates significantly from baseline, emit a medium-severity signal.
    Caller should control probes ('1' vs \"' OR '1'='1\") and pass the probed page as page and the baseline length.
    """
    findings: List[FindingRecord] = []
    try:
        parsed = urlparse(page.url or "")
        params = parse_qsl(parsed.query, keep_blank_values=True)
        if len(params) != 1:
            return findings
        body_len = len(page.body_excerpt or "")
        # Tight threshold: 20% change and absolute delta at least 50 bytes
        if baseline_len > 0:
            delta = abs(body_len - baseline_len)
            ratio = delta / max(1, baseline_len)
            if delta >= 50 and ratio >= 0.2:
                findings.append(
                    FindingRecord(
                        plugin_key="dynamic.crawler.sqli",
                        category="injection.sqli.length",
                        title="Possible SQL injection (length-based signal)",
                        description=f"Response length changed significantly compared to baseline on {page.url}",
                        severity="medium",
                        location=page.url,
                        metadata={"baseline_len": baseline_len, "observed_len": body_len},
                        compliance_tags=["A03:2021-Injection"],
                        evidence=[_evidence_from_page(page, {"probe": json.dumps({"baseline_len": baseline_len, "observed_len": body_len})})],
                    )
                )
    except Exception:
        # Pure function: swallow exceptions and return empty
        return findings

    return findings