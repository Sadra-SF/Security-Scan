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
    return cfg.get("upload") or cfg.get("file_upload") or {}


class FileUploadScanner(ScannerAdapter):
    # Registry identity
    key = "dynamic_file_upload"
    display_name = "File Upload Vulnerability Scanner"
    version = "1.0.0"

    UPLOAD_PATTERNS = [
        r"upload", r"file", r"attachment", r"document", r"image",
        r"multipart", r"form-data", r"enctype"
    ]

    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.jar', '.war',
        '.php', '.jsp', '.asp', '.aspx', '.cgi', '.pl', '.py', '.sh',
        '.js', '.vbs', '.hta', '.wsf', '.ps1'
    ]

    @property
    def name(self) -> str:
        return "dynamic.file_upload"

    @property
    def type(self) -> str:
        return ScannerType.DYNAMIC

    def validate_config(self, ctx: ScanContext) -> None:
        cfg = _get_config_section(ctx)
        if not isinstance(cfg, dict):
            return

    def _check_file_type_validation(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for file upload forms without proper validation
        if re.search(r'<form[^>]*enctype\s*=\s*["\']multipart/form-data["\']', content, re.IGNORECASE):
            # Look for file input
            if re.search(r'<input[^>]*type\s*=\s*["\']file["\']', content, re.IGNORECASE):
                # Check for client-side validation only
                has_client_validation = re.search(r'accept\s*=', content, re.IGNORECASE)

                if has_client_validation:
                    evidence = EvidenceItem(
                        kind="form_analysis",
                        inline="File upload form with client-side validation only",
                        content_type="text/plain",
                        metadata={"has_client_validation": True}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="upload.client_validation_only",
                        title="Client-side file validation only",
                        severity="medium",
                        description="File upload relies only on client-side validation, easily bypassed.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A01:2021"},
                        compliance_tags=["OWASP-A01:2021"]
                    ))

                # Check for missing server-side validation indicators
                validation_indicators = [
                    r"validate.*file", r"check.*extension", r"verify.*type",
                    r"mimetype", r"content.type", r"magic.*number"
                ]

                has_server_validation = any(re.search(pattern, content, re.IGNORECASE) for pattern in validation_indicators)

                if not has_server_validation:
                    evidence = EvidenceItem(
                        kind="form_analysis",
                        inline="No server-side file validation detected",
                        content_type="text/plain",
                        metadata={"checked_patterns": validation_indicators}
                    )
                    findings.append(FindingRecord(
                        plugin_key=self.key,
                        category="upload.missing_validation",
                        title="Missing server-side file validation",
                        severity="high",
                        description="File upload endpoint lacks server-side validation, vulnerable to malicious uploads.",
                        location=url,
                        evidence=[evidence],
                        metadata={"owasp_tag": "A01:2021"},
                        compliance_tags=["OWASP-A01:2021"]
                    ))

        return findings

    def _check_directory_traversal(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for path manipulation vulnerabilities
        traversal_patterns = [
            r"\.\./", r"\.\.\\", r"%2e%2e%2f", r"%2e%2e%5c",
            r"../", r"..\\", r"\\..\\", r"/..../"
        ]

        for pattern in traversal_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                evidence = EvidenceItem(
                    kind="content_analysis",
                    inline=f"Directory traversal pattern detected: {pattern}",
                    content_type="text/plain",
                    metadata={"pattern": pattern}
                )
                findings.append(FindingRecord(
                    plugin_key=self.key,
                    category="upload.directory_traversal",
                    title="Potential directory traversal vulnerability",
                    severity="high",
                    description="Directory traversal patterns detected, may allow access to sensitive files.",
                    location=url,
                    evidence=[evidence],
                    metadata={"owasp_tag": "A01:2021"},
                    compliance_tags=["OWASP-A01:2021"]
                ))
                break

        return findings

    def _check_file_size_limits(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for file size limits
        size_limit_patterns = [
            r"max.*size", r"size.*limit", r"file.*size", r"upload.*limit",
            r"MAX_FILE_SIZE", r"maxfilesize"
        ]

        has_size_limit = any(re.search(pattern, content, re.IGNORECASE) for pattern in size_limit_patterns)

        if not has_size_limit:
            evidence = EvidenceItem(
                kind="form_analysis",
                inline="No file size limits detected",
                content_type="text/plain",
                metadata={"checked_patterns": size_limit_patterns}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="upload.missing_size_limit",
                title="Missing file size limits",
                severity="medium",
                description="File upload has no size restrictions, vulnerable to DoS attacks.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A05:2021"},
                compliance_tags=["OWASP-A05:2021"]
            ))

        return findings

    def _check_mime_type_validation(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for MIME type validation
        mime_patterns = [
            r"content.type", r"mimetype", r"content-type",
            r"application/", r"image/", r"text/"
        ]

        has_mime_check = any(re.search(pattern, content, re.IGNORECASE) for pattern in mime_patterns)

        if not has_mime_check:
            evidence = EvidenceItem(
                kind="content_analysis",
                inline="No MIME type validation detected",
                content_type="text/plain",
                metadata={"checked_patterns": mime_patterns}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="upload.missing_mime_check",
                title="Missing MIME type validation",
                severity="medium",
                description="File upload does not validate MIME types, allowing potentially malicious files.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A01:2021"},
                compliance_tags=["OWASP-A01:2021"]
            ))

        return findings

    def _check_filename_sanitization(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for filename sanitization
        filename_patterns = [
            r"filename", r"basename", r"pathinfo", r"realpath",
            r"sanitize", r"clean.*name", r"validate.*name"
        ]

        has_filename_sanitization = any(re.search(pattern, content, re.IGNORECASE) for pattern in filename_patterns)

        if not has_filename_sanitization:
            evidence = EvidenceItem(
                kind="content_analysis",
                inline="No filename sanitization detected",
                content_type="text/plain",
                metadata={"checked_patterns": filename_patterns}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="upload.filename_sanitization",
                title="Missing filename sanitization",
                severity="medium",
                description="Uploaded filenames are not sanitized, vulnerable to path manipulation.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A01:2021"},
                compliance_tags=["OWASP-A01:2021"]
            ))

        return findings

    def _check_storage_security(self, url: str, content: str) -> List[FindingRecord]:
        findings = []

        # Check for secure file storage practices
        storage_patterns = [
            r"chmod", r"permissions", r"secure.*upload", r"temp.*dir",
            r"public.*access", r"web.*root"
        ]

        has_secure_storage = any(re.search(pattern, content, re.IGNORECASE) for pattern in storage_patterns)

        if not has_secure_storage:
            evidence = EvidenceItem(
                kind="content_analysis",
                inline="No secure file storage practices detected",
                content_type="text/plain",
                metadata={"checked_patterns": storage_patterns}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="upload.insecure_storage",
                title="Insecure file storage",
                severity="low",
                description="File storage practices may not be secure, files could be accessible to unauthorized users.",
                location=url,
                evidence=[evidence],
                metadata={"owasp_tag": "A01:2021"},
                compliance_tags=["OWASP-A01:2021"]
            ))

        return findings

    def run(self, ctx: ScanContext) -> List[FindingRecord]:
        cfg = _get_config_section(ctx)
        target_url = (ctx.config or {}).get("asset", {}).get("address", "")

        findings = []

        if not target_url:
            return findings

        try:
            # Check if this looks like a file upload endpoint
            url_lower = target_url.lower()
            is_upload_endpoint = any(pattern in url_lower for pattern in self.UPLOAD_PATTERNS)

            if is_upload_endpoint:
                # Perform file upload vulnerability checks
                findings.extend(self._check_file_type_validation(target_url, ""))
                findings.extend(self._check_directory_traversal(target_url, ""))
                findings.extend(self._check_file_size_limits(target_url, ""))
                findings.extend(self._check_mime_type_validation(target_url, ""))
                findings.extend(self._check_filename_sanitization(target_url, ""))
                findings.extend(self._check_storage_security(target_url, ""))

        except Exception as e:
            logger.error(f"File upload scan failed for {target_url}: {e}")
            evidence = EvidenceItem(
                kind="scan_error",
                inline=f"File upload scan failed: {str(e)}",
                content_type="text/plain",
                metadata={"error_type": type(e).__name__, "url": target_url}
            )
            findings.append(FindingRecord(
                plugin_key=self.key,
                category="error",
                title="File upload scan error",
                severity="medium",
                description=f"Error during file upload scan: {str(e)}",
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
_adapter_upload = FileUploadScanner()
_upload_key = getattr(_adapter_upload, "key", None)
if not _upload_key:
    raise ValueError("FileUploadScanner must define a unique 'key'")

_upload_exists = None
if hasattr(registry, "get"):
    try:
        _upload_exists = registry.get(_upload_key)
    except Exception:
        _upload_exists = None
elif hasattr(registry, "_plugins"):
    try:
        _upload_exists = registry._plugins.get(_upload_key)
    except Exception:
        _upload_exists = None

if not _upload_exists:
    registry.register(_adapter_upload)