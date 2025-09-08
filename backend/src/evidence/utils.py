"""
Evidence collection utilities for scanners.
"""
from typing import Dict, Any, Optional
from scanners.types import EvidenceItem


def create_screenshot_evidence(
    url: str,
    title: Optional[str] = None,
    browser: str = "chrome",
    headless: bool = True,
    wait_time: int = 5,
    full_page: bool = False,
    element_selector: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EvidenceItem:
    """
    Create an EvidenceItem for screenshot capture.

    Args:
        url: URL to capture screenshot of
        title: Title for the evidence
        browser: Browser to use ('chrome' or 'firefox')
        headless: Whether to run in headless mode
        wait_time: Time to wait for page load (seconds)
        full_page: Whether to capture full page
        element_selector: CSS selector for specific element
        metadata: Additional metadata

    Returns:
        EvidenceItem configured for screenshot capture
    """
    evidence_metadata = {
        "capture_url": url,
        "browser": browser,
        "headless": headless,
        "wait_time": wait_time,
        "full_page": full_page,
        "title": title,
    }

    if element_selector:
        evidence_metadata["element_selector"] = element_selector

    if metadata:
        evidence_metadata.update(metadata)

    return EvidenceItem(
        kind="screenshot",
        content_type="image/png",
        metadata=evidence_metadata
    )


def create_request_response_evidence(
    request_data: Dict[str, Any],
    response_data: Dict[str, Any],
    url: str,
    method: str = "GET",
    status_code: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> EvidenceItem:
    """
    Create an EvidenceItem for HTTP request/response data.

    Args:
        request_data: Request details (headers, body, etc.)
        response_data: Response details (headers, body, status, etc.)
        url: Request URL
        method: HTTP method
        status_code: Response status code
        metadata: Additional metadata

    Returns:
        EvidenceItem with request/response data
    """
    evidence_metadata = {
        "url": url,
        "method": method,
        "status_code": status_code,
        "request": request_data,
        "response": response_data,
    }

    if metadata:
        evidence_metadata.update(metadata)

    return EvidenceItem(
        kind="request_response",
        content_type="application/json",
        metadata=evidence_metadata
    )


def create_log_evidence(
    log_data: str,
    log_type: str = "general",
    metadata: Optional[Dict[str, Any]] = None
) -> EvidenceItem:
    """
    Create an EvidenceItem for log data.

    Args:
        log_data: Log content
        log_type: Type of log (e.g., 'access', 'error', 'debug')
        metadata: Additional metadata

    Returns:
        EvidenceItem with log data
    """
    evidence_metadata = {
        "log_type": log_type,
    }

    if metadata:
        evidence_metadata.update(metadata)

    return EvidenceItem(
        kind="log",
        inline=log_data,
        content_type="text/plain",
        metadata=evidence_metadata
    )


def create_artifact_evidence(
    content: str,
    filename: str,
    content_type: str = "text/plain",
    metadata: Optional[Dict[str, Any]] = None
) -> EvidenceItem:
    """
    Create an EvidenceItem for artifacts (files, configurations, etc.).

    Args:
        content: Artifact content
        filename: Original filename
        content_type: MIME type
        metadata: Additional metadata

    Returns:
        EvidenceItem with artifact data
    """
    evidence_metadata = {
        "filename": filename,
    }

    if metadata:
        evidence_metadata.update(metadata)

    return EvidenceItem(
        kind="artifact",
        inline=content,
        content_type=content_type,
        metadata=evidence_metadata
    )