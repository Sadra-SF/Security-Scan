from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from ..base import ScannerAdapter, ScanContext
from ..constants import ScannerType, Severity
from .. import registry
from ..types import FindingRecord, EvidenceItem

logger = logging.getLogger(__name__)


def _get_config_section(ctx: ScanContext) -> Dict[str, Any]:
    cfg = ctx.config or {}
    return cfg.get("auth") or cfg.get("authentication") or {}


class AuthenticationScanner(ScannerAdapter):
    # Registry identity
    key = "dynamic_auth"
    display_name = "Authentication Security Scanner"
    version = "1.0.0"

    AUTH_PATTERNS = [
        r"login", r"logon", r"signin", r"signon", r"auth", r"authenticate",
        r"session", r"token", r"cookie", r"jwt", r"oauth", r"saml"
    ]

    @property
    def name(self) -> str:
        return "dynamic.auth"

    @property
    def type(self) -> str:
        return ScannerType.DYNAMIC

    def validate_config(self, ctx: ScanContext) -> None:
        cfg = _get_config_section(ctx)
        if not isinstance(cfg, dict):
            return

    def _check_session_management(self, url: str, response_headers: Dict[str, str]) -> List[FindingRecord]:
        findings = []

        # Check for secure cookie attributes
        cookies = []
        set_cookie = response_headers.get('Set-Cookie', '')
        if set_cookie:
            cookies = [c.strip() for c in set_cookie.split(',')]

        for cookie in cookies:
            cookie_lower = cookie.lower()

            # Check for missing Secure flag on sensitive cookies
            if any(pattern in cookie_lower for pattern in ['session', 'auth', 'token', 'jwt']):
                if 'secure' not in cookie_lower:
                    evidence = EvidenceItem(
                        kind="cookie_analysis",
                        inline=f"Cookie missing Secure flag: {cookie}",
                        content_type="text/plain",
                        metadata={"cookie": cookie, "missing_flags": ["secure"]}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="auth.session_insecure",
                        title="Session cookie missing Secure flag",
                        severity="medium",
                        description="Session or authentication cookie is missing the Secure flag, allowing transmission over HTTP.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A02:2021"},
                        compliance_tags=["OWASP-A02:2021"]
                    ))

                if 'httponly' not in cookie_lower:
                    evidence = EvidenceItem(
                        kind="cookie_analysis",
                        inline=f"Cookie missing HttpOnly flag: {cookie}",
                        content_type="text/plain",
                        metadata={"cookie": cookie, "missing_flags": ["httponly"]}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="auth.session_insecure",
                        title="Session cookie missing HttpOnly flag",
                        severity="medium",
                        description="Session or authentication cookie is missing the HttpOnly flag, vulnerable to XSS attacks.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A02:2021"},
                        compliance_tags=["OWASP-A02:2021"]
                    ))

                if 'samesite' not in cookie_lower:
                    evidence = EvidenceItem(
                        kind="cookie_analysis",
                        inline=f"Cookie missing SameSite flag: {cookie}",
                        content_type="text/plain",
                        metadata={"cookie": cookie, "missing_flags": ["samesite"]}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="auth.csrf_weak",
                        title="Cookie missing SameSite attribute",
                        severity="low",
                        description="Cookie is missing SameSite attribute, potentially vulnerable to CSRF attacks.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A01:2021"},
                        compliance_tags=["OWASP-A01:2021"]
                    ))

        return findings

    def _check_authentication_headers(self, url: str, response_headers: Dict[str, str]) -> List[FindingRecord]:
        findings = []

        # Check for weak authentication methods
        auth_header = response_headers.get('WWW-Authenticate', '')
        if auth_header:
            if 'basic' in auth_header.lower():
                evidence = EvidenceItem(
                    kind="auth_header",
                    inline=f"Weak authentication method: {auth_header}",
                    content_type="text/plain",
                    metadata={"auth_method": "basic"}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="auth.weak_method",
                    title="Weak authentication method detected",
                    severity="medium",
                    description="HTTP Basic authentication detected. Consider using stronger authentication methods.",
                    location=url,
                    evidence=[evidence],
                    metadata={"owasp_tag": "A02:2021"},
                    compliance_tags=["OWASP-A02:2021"]
                ))

        return findings

    def _check_logout_functionality(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for logout links/forms
        logout_patterns = [r"logout", r"sign.?out", r"log.?out", r"signoff"]
        has_logout = any(re.search(pattern, content, re.IGNORECASE) for pattern in logout_patterns)

        if not has_logout:
            evidence = EvidenceItem(
                kind="content_analysis",
                inline="No logout functionality detected in page content",
                content_type="text/plain",
                metadata={"checked_patterns": logout_patterns}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="auth.missing_logout",
                title="Missing logout functionality",
                severity="low",
                description="No logout functionality detected on authenticated pages.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A07:2021"},
                compliance_tags=["OWASP-A07:2021"]
            ))

        return findings

    def _check_password_policy_indicators(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for password strength requirements
        weak_indicators = [
            r"password.*must.*be.*at.*least.*\d+.*characters",
            r"password.*minimum.*length",
            r"password.*complexity"
        ]

        has_password_policy = any(re.search(pattern, content, re.IGNORECASE) for pattern in weak_indicators)

        if not has_password_policy:
            evidence = EvidenceItem(
                kind="content_analysis",
                inline="No visible password policy requirements detected",
                content_type="text/plain",
                metadata={"checked_patterns": weak_indicators}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="auth.weak_password_policy",
                title="Weak password policy indicators",
                severity="low",
                description="No visible password strength requirements detected.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A02:2021"},
                compliance_tags=["OWASP-A02:2021"]
            ))

        return findings

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        target_url = (ctx.config or {}).get("asset", {}).get("address", "")

        findings = []

        if not target_url:
            return findings

        # Simulate HTTP request to check authentication
        try:
            # For now, we'll analyze the URL and assume some basic checks
            # In a real implementation, this would make actual HTTP requests

            # Check URL for authentication patterns
            url_lower = target_url.lower()
            if any(pattern in url_lower for pattern in self.AUTH_PATTERNS):
                # This looks like an authentication endpoint
                findings.extend(self._check_session_management(target_url, {}))
                findings.extend(self._check_authentication_headers(target_url, {}))
                findings.extend(self._check_logout_functionality(target_url, ""))
                findings.extend(self._check_password_policy_indicators(target_url, ""))

        except Exception as e:
            logger.error(f"Authentication scan failed for {target_url}: {e}")
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"Authentication scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "url": target_url}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="Authentication scan error",
                severity="medium",
                description=f"Error during authentication scan: {str(e)}",
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
_adapter_auth = AuthenticationScanner()
_auth_key = getattr(_adapter_auth, "key", None)
if not _auth_key:
    raise ValueError("AuthenticationScanner must define a unique 'key'")

_auth_exists = None
if hasattr(registry, "get"):
    try:
        _auth_exists = registry.get(_auth_key)
    except Exception:
        _auth_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _auth_exists = registry._plugins.get(_auth_key)
    except Exception:
        _auth_exists = None

if not _auth_exists:
    registry.register(_adapter_auth)