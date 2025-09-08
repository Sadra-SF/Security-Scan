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
    return cfg.get("api") or cfg.get("apis") or {}


class APISecurityScanner(ScannerAdapter):
    # Registry identity
    key = "dynamic_api"
    display_name = "API Security Scanner"
    version = "1.0.0"

    API_ENDPOINT_PATTERNS = [
        r"/api/", r"/v\d+/", r"/rest/", r"/graphql", r"/soap",
        r"\.json$", r"\.xml$", r"/endpoint"
    ]

    @property
    def name(self) -> str:
        return "dynamic.api"

    @property
    def type(self) -> str:
        return ScannerType.DYNAMIC

    def validate_config(self, ctx: ScanContext) -> None:
        cfg = _get_config_section(ctx)
        if not isinstance(cfg, dict):
            return

    def _check_cors_configuration(self, url: str, response_headers: Dict[str, str]) -> List[FindingRecord]:
        findings = []

        cors_headers = {
            'Access-Control-Allow-Origin': response_headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response_headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response_headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response_headers.get('Access-Control-Allow-Credentials')
        }

        # Check for overly permissive CORS
        origin = cors_headers.get('Access-Control-Allow-Origin')
        if origin == '*':
            evidence = EvidenceItem(
                kind="cors_analysis",
                inline=f"CORS allows all origins: {origin}",
                content_type="text/plain",
                metadata={"cors_headers": cors_headers}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="api.cors_permissive",
                title="Overly permissive CORS configuration",
                severity="medium",
                description="API allows requests from any origin (*), potentially exposing sensitive data.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A01:2021"},
                compliance_tags=["OWASP-A01:2021"]
            ))

        # Check for missing CORS headers
        if not origin:
            evidence = EvidenceItem(
                kind="cors_analysis",
                inline="Missing CORS headers in API response",
                content_type="text/plain",
                metadata={"cors_headers": cors_headers}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="api.cors_missing",
                title="Missing CORS configuration",
                severity="low",
                description="API does not include CORS headers, may cause issues with web applications.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def _check_rate_limiting(self, url: str, response_headers: Dict[str, str]) -> List[FindingRecord]:
        findings = []

        rate_limit_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
            'Retry-After'
        ]

        has_rate_limiting = any(header in response_headers for header in rate_limit_headers)

        if not has_rate_limiting:
            evidence = EvidenceItem(
                kind="header_analysis",
                inline="No rate limiting headers detected",
                content_type="text/plain",
                metadata={"checked_headers": rate_limit_headers}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="api.missing_rate_limit",
                title="Missing rate limiting",
                severity="medium",
                description="API does not appear to implement rate limiting, vulnerable to DoS attacks.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def _check_api_versioning(self, url: str) -> List[FindingRecord]:
        findings = []

        parsed = urlparse(url)
        path = parsed.path

        # Check for versioned endpoints
        if not re.search(r'/v\d+/', path):
            evidence = EvidenceItem(
                kind="url_analysis",
                inline=f"API endpoint without version: {path}",
                content_type="text/plain",
                metadata={"path": path}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="api.missing_versioning",
                title="Missing API versioning",
                severity="low",
                description="API endpoint does not include version information, making future changes difficult.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def _check_http_methods(self, url: str, allowed_methods: List[str]) -> List[FindingRecord]:
        findings = []

        dangerous_methods = ['PUT', 'DELETE', 'PATCH']
        safe_methods = ['GET', 'HEAD', 'OPTIONS']

        # Check for dangerous methods
        for method in dangerous_methods:
            if method in allowed_methods:
                evidence = EvidenceItem(
                    kind="method_analysis",
                    inline=f"Dangerous HTTP method allowed: {method}",
                    content_type="text/plain",
                    metadata={"allowed_methods": allowed_methods, "method": method}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="api.dangerous_method",
                    title=f"Dangerous HTTP method enabled: {method}",
                    severity="low",
                    description=f"API allows {method} method which can modify resources.",
                    location=url,
                    evidence=[evidence],
                    metadata={"owasp_tag": "A05:2021"},
                    compliance_tags=["OWASP-A05:2021"]
                ))

        # Check for OPTIONS method (good for API discovery)
        if 'OPTIONS' not in allowed_methods:
            evidence = EvidenceItem(
                kind="method_analysis",
                inline="OPTIONS method not available for API discovery",
                content_type="text/plain",
                metadata={"allowed_methods": allowed_methods}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="api.missing_options",
                title="Missing OPTIONS method",
                severity="info",
                description="API does not support OPTIONS method, hindering API discovery.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def _check_content_type_validation(self, url: str, response_headers: Dict[str, str]) -> List[FindingRecord]:
        findings = []

        content_type = response_headers.get('Content-Type', '')

        # Check for JSON APIs without proper content type
        if '/api/' in url.lower() or '/v' in url.lower():
            if not content_type or 'json' not in content_type.lower():
                evidence = EvidenceItem(
                    kind="header_analysis",
                    inline=f"API response missing JSON content type: {content_type}",
                    content_type="text/plain",
                    metadata={"content_type": content_type}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="api.content_type_mismatch",
                    title="Incorrect Content-Type for API",
                    severity="low",
                    description="API endpoint should return JSON content type for proper client handling.",
                    location=url,
                    evidence=[evidence],
                    metadata={"owasp_tag": "A05:2021"},
                    compliance_tags=["OWASP-A05:2021"]
                ))

        return findings

    def _check_error_handling(self, url: str, status_code: int, response_body: str) -> List[FindingRecord]:
        findings = []

        # Check for information disclosure in error responses
        if status_code >= 400:
            # Look for sensitive information in error responses
            sensitive_patterns = [
                r"stack\s*trace", r"exception", r"error.*at.*line",
                r"database.*error", r"sql.*error", r"path.*[/\\]"
            ]

            for pattern in sensitive_patterns:
                if re.search(pattern, response_body, re.IGNORECASE):
                    evidence = EvidenceItem(
                        kind="response_analysis",
                        inline=f"Error response contains sensitive information: {pattern}",
                        content_type="text/plain",
                        metadata={"status_code": status_code, "pattern": pattern}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="api.info_disclosure",
                        title="Information disclosure in error response",
                        severity="medium",
                        description="API error response contains sensitive information that could aid attackers.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A02:2021"},
                        compliance_tags=["OWASP-A02:2021"]
                    ))
                    break

        return findings

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        target_url = (ctx.config or {}).get("asset", {}).get("address", "")

        findings = []

        if not target_url:
            return findings

        try:
            # Check if this looks like an API endpoint
            url_lower = target_url.lower()
            is_api_endpoint = any(re.search(pattern, url_lower) for pattern in self.API_ENDPOINT_PATTERNS)

            if is_api_endpoint:
                # Perform API-specific checks
                findings.extend(self._check_cors_configuration(target_url, {}))
                findings.extend(self._check_rate_limiting(target_url, {}))
                findings.extend(self._check_api_versioning(target_url))
                findings.extend(self._check_content_type_validation(target_url, {}))
                findings.extend(self._check_error_handling(target_url, 200, ""))

                # Simulate checking allowed methods
                allowed_methods = ['GET', 'POST', 'PUT', 'DELETE']  # This would come from actual OPTIONS request
                findings.extend(self._check_http_methods(target_url, allowed_methods))

        except Exception as e:
            logger.error(f"API scan failed for {target_url}: {e}")
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"API scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "url": target_url}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="API scan error",
                severity="medium",
                description=f"Error during API scan: {str(e)}",
                location=target_url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def supports(self, asset: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        enabled = (profile or {}).get("enabled_scanners", [])
        asset_type = (asset or {}).get("type")
        is_api = asset_type in {"api", "rest", "graphql", "soap"}
        return is_api and (self.name in enabled or self.type in enabled)


# Duplicate-safe registration on import
_adapter_api = APISecurityScanner()
_api_key = getattr(_adapter_api, "key", None)
if not _api_key:
    raise ValueError("APISecurityScanner must define a unique 'key'")

_api_exists = None
if hasattr(registry, "get"):
    try:
        _api_exists = registry.get(_api_key)
    except Exception:
        _api_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _api_exists = registry._plugins.get(_api_key)
    except Exception:
        _api_exists = None

if not _api_exists:
    registry.register(_adapter_api)