"""
HTTP request/response logging utilities for comprehensive evidence collection.
"""
import json
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

import requests
from urllib.parse import urlparse

from .utils import create_request_response_evidence
from scanners.types import EvidenceItem

logger = logging.getLogger(__name__)


class HTTPLogger:
    """Enhanced HTTP logging with comprehensive request/response capture."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def log_request_response(
        self,
        method: str,
        url: str,
        request_headers: Optional[Dict[str, str]] = None,
        request_body: Optional[Union[str, bytes]] = None,
        response: Optional[requests.Response] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceItem:
        """
        Create comprehensive HTTP request/response evidence.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            request_headers: Request headers
            request_body: Request body content
            response: Response object (if available)
            start_time: Request start time
            end_time: Response end time
            error: Error message if request failed
            metadata: Additional metadata

        Returns:
            EvidenceItem with comprehensive HTTP details
        """
        request_data = {
            "method": method,
            "url": url,
            "headers": request_headers or {},
            "timestamp": start_time.isoformat() if start_time else datetime.now(timezone.utc).isoformat(),
        }

        # Add request body if present
        if request_body:
            if isinstance(request_body, bytes):
                try:
                    # Try to decode as UTF-8
                    request_data["body"] = request_body.decode('utf-8')
                    request_data["body_encoding"] = "utf-8"
                except UnicodeDecodeError:
                    # If not UTF-8, store as base64
                    import base64
                    request_data["body"] = base64.b64encode(request_body).decode('ascii')
                    request_data["body_encoding"] = "base64"
            else:
                request_data["body"] = str(request_body)

        response_data = {}
        status_code = None

        if response:
            status_code = response.status_code
            response_data = {
                "status_code": status_code,
                "headers": dict(response.headers),
                "timestamp": end_time.isoformat() if end_time else datetime.now(timezone.utc).isoformat(),
            }

            # Calculate timing
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds() * 1000  # milliseconds
                response_data["duration_ms"] = round(duration, 2)

            # Capture response body (with size limits)
            try:
                content_length = len(response.content)
                response_data["content_length"] = content_length

                # Store response body based on content type and size
                content_type = response.headers.get('content-type', '').lower()

                if content_length > 100 * 1024:  # 100KB limit
                    response_data["body"] = f"[Content too large: {content_length} bytes]"
                    response_data["body_truncated"] = True
                elif 'json' in content_type:
                    try:
                        response_data["body"] = response.json()
                        response_data["body_format"] = "json"
                    except:
                        response_data["body"] = response.text[:5000]
                        response_data["body_truncated"] = content_length > 5000
                elif 'text' in content_type or 'html' in content_type or 'xml' in content_type:
                    response_data["body"] = response.text[:10000]
                    response_data["body_truncated"] = len(response.text) > 10000
                else:
                    # Binary content
                    if content_length <= 1024:  # Small binary files
                        import base64
                        response_data["body"] = base64.b64encode(response.content).decode('ascii')
                        response_data["body_encoding"] = "base64"
                    else:
                        response_data["body"] = f"[Binary content: {content_length} bytes]"
                        response_data["body_binary"] = True

            except Exception as e:
                response_data["body_error"] = str(e)
                logger.warning(f"Failed to capture response body: {e}")

        elif error:
            response_data = {
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Prepare metadata
        evidence_metadata = {
            "http_method": method,
            "url": url,
            "domain": urlparse(url).netloc,
            "status_code": status_code,
            "has_request_body": bool(request_body),
            "has_response_body": bool(response and response.content),
            "request_headers_count": len(request_headers or {}),
            "response_headers_count": len(response.headers) if response else 0,
        }

        if start_time and end_time:
            evidence_metadata["duration_ms"] = round((end_time - start_time).total_seconds() * 1000, 2)

        if metadata:
            evidence_metadata.update(metadata)

        return create_request_response_evidence(
            request_data=request_data,
            response_data=response_data,
            url=url,
            method=method,
            status_code=status_code,
            metadata=evidence_metadata
        )

    def log_from_response(
        self,
        response: requests.Response,
        request_body: Optional[Union[str, bytes]] = None,
        start_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceItem:
        """
        Create evidence from a requests Response object.

        Args:
            response: The response object
            request_body: Original request body
            start_time: Request start time
            metadata: Additional metadata

        Returns:
            EvidenceItem with HTTP details
        """
        # Extract request details from response
        request = response.request
        method = request.method or "GET"
        url = request.url or ""
        request_headers = dict(request.headers)

        end_time = datetime.now(timezone.utc)

        return self.log_request_response(
            method=method,
            url=url,
            request_headers=request_headers,
            request_body=request_body,
            response=response,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata
        )


def create_http_evidence_from_session(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs
) -> EvidenceItem:
    """
    Convenience function to create HTTP evidence by making a request.

    Args:
        session: Requests session to use
        method: HTTP method
        url: URL to request
        **kwargs: Additional arguments for session.request()

    Returns:
        EvidenceItem with HTTP details
    """
    logger = HTTPLogger(session)
    start_time = datetime.now(timezone.utc)

    try:
        response = session.request(method, url, **kwargs)
        end_time = datetime.now(timezone.utc)

        # Extract request body from kwargs if present
        request_body = kwargs.get('data') or kwargs.get('json')

        return logger.log_request_response(
            method=method,
            url=url,
            request_headers=dict(response.request.headers),
            request_body=request_body,
            response=response,
            start_time=start_time,
            end_time=end_time
        )
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        return logger.log_request_response(
            method=method,
            url=url,
            request_headers=kwargs.get('headers'),
            request_body=kwargs.get('data') or kwargs.get('json'),
            error=str(e),
            start_time=start_time,
            end_time=end_time
        )