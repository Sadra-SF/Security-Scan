"""
Evidence metadata enrichment utilities.
"""
import platform
import socket
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import hashlib
import json

from .models import Evidence


class EvidenceEnricher:
    """Enrich evidence with comprehensive metadata."""

    @staticmethod
    def enrich_evidence(evidence: Evidence, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Enrich evidence with comprehensive metadata.

        Args:
            evidence: Evidence instance to enrich
            context: Additional context information
        """
        metadata = evidence.metadata.copy() if evidence.metadata else {}

        # Basic enrichment
        metadata.update(EvidenceEnricher._get_basic_metadata())

        # Environment enrichment
        metadata.update(EvidenceEnricher._get_environment_metadata())

        # Context-specific enrichment
        if context:
            metadata.update(EvidenceEnricher._get_context_metadata(context))

        # Evidence-specific enrichment
        metadata.update(EvidenceEnricher._get_evidence_specific_metadata(evidence))

        # Generate unique identifiers
        if not metadata.get('evidence_uuid'):
            metadata['evidence_uuid'] = str(uuid.uuid4())

        # Add processing timestamps
        now = datetime.now(timezone.utc)
        if not metadata.get('enriched_at'):
            metadata['enriched_at'] = now.isoformat()

        evidence.metadata = metadata
        evidence.save(update_fields=['metadata'])

    @staticmethod
    def _get_basic_metadata() -> Dict[str, Any]:
        """Get basic metadata about the system and processing."""
        return {
            'enrichment_version': '1.0',
            'processed_by': 'EvidenceEnricher',
            'processing_timestamp': datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _get_environment_metadata() -> Dict[str, Any]:
        """Get environment-specific metadata."""
        try:
            return {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version(),
                },
                'hostname': socket.gethostname(),
                'ip_address': EvidenceEnricher._get_local_ip(),
                'timezone': str(timezone.utc),  # Could be made configurable
            }
        except Exception as e:
            return {
                'environment_error': str(e),
                'platform': platform.system(),
            }

    @staticmethod
    def _get_context_metadata(context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and enrich context-specific metadata."""
        enriched_context = {}

        # Scan context
        if 'scan_id' in context:
            enriched_context['scan_id'] = context['scan_id']
            enriched_context['scan_context'] = 'active'

        # Target context
        if 'target' in context:
            target = context['target']
            enriched_context['target_info'] = {
                'address': getattr(target, 'address', None),
                'target_type': getattr(target, 'target_type', None),
                'tags': getattr(target, 'tags', []),
            }

        # User context
        if 'user' in context:
            user = context['user']
            enriched_context['user_info'] = {
                'username': getattr(user, 'username', None),
                'user_id': getattr(user, 'id', None),
                'is_staff': getattr(user, 'is_staff', False),
            }

        # HTTP context
        if 'http_request' in context:
            request = context['http_request']
            enriched_context['http_context'] = {
                'method': getattr(request, 'method', None),
                'path': getattr(request, 'path', None),
                'user_agent': EvidenceEnricher._extract_user_agent(request),
                'remote_addr': EvidenceEnricher._extract_remote_addr(request),
                'headers': EvidenceEnricher._extract_safe_headers(request),
            }

        # Scanner context
        if 'scanner' in context:
            scanner = context['scanner']
            enriched_context['scanner_info'] = {
                'name': getattr(scanner, 'name', None),
                'version': getattr(scanner, 'version', None),
                'type': getattr(scanner, 'type', None),
            }

        return enriched_context

    @staticmethod
    def _get_evidence_specific_metadata(evidence: Evidence) -> Dict[str, Any]:
        """Get metadata specific to the evidence type."""
        metadata = {}

        # File-based evidence
        if evidence.file:
            metadata['file_info'] = {
                'original_name': evidence.file.name,
                'size': evidence.size,
                'content_type': evidence.content_type,
                'has_file': True,
            }

            # Generate file hash if not present
            if not evidence.sha256 and evidence.file.path:
                try:
                    with open(evidence.file.path, 'rb') as f:
                        content = f.read()
                        evidence.sha256 = hashlib.sha256(content).hexdigest()
                        metadata['file_hash_calculated'] = True
                except Exception as e:
                    metadata['file_hash_error'] = str(e)

        # URL-based evidence
        if evidence.storage_url and evidence.storage_url.startswith(('http://', 'https://')):
            metadata['url_info'] = {
                'scheme': evidence.storage_url.split('://')[0],
                'is_external': True,
            }

        # Kind-specific metadata
        if evidence.kind == 'screenshot':
            metadata['screenshot_info'] = {
                'capture_method': 'selenium',
                'expected_format': 'png',
            }
        elif evidence.kind == 'request_response':
            metadata['http_info'] = {
                'has_request': bool(evidence.metadata.get('request')),
                'has_response': bool(evidence.metadata.get('response')),
                'status_code': evidence.metadata.get('status_code'),
            }
        elif evidence.kind == 'log':
            metadata['log_info'] = {
                'log_type': evidence.metadata.get('log_type', 'general'),
                'estimated_lines': len(evidence.metadata.get('inline', '').split('\n')) if evidence.metadata.get('inline') else 0,
            }

        # Correlation metadata
        if evidence.correlation_id:
            metadata['correlation_info'] = {
                'correlation_id': evidence.correlation_id,
                'correlation_type': evidence.correlation_type,
                'is_correlated': True,
            }

        # Finding relationship metadata
        if evidence.finding:
            metadata['finding_info'] = {
                'finding_id': str(evidence.finding.id),
                'severity': evidence.finding.severity,
                'status': evidence.finding.status,
                'title': evidence.finding.title[:100],  # Truncate for metadata
            }

        return metadata

    @staticmethod
    def _get_local_ip() -> Optional[str]:
        """Get the local IP address."""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    @staticmethod
    def _extract_user_agent(request) -> Optional[str]:
        """Extract user agent from request."""
        try:
            return getattr(request, 'META', {}).get('HTTP_USER_AGENT')
        except Exception:
            return None

    @staticmethod
    def _extract_remote_addr(request) -> Optional[str]:
        """Extract remote address from request."""
        try:
            return getattr(request, 'META', {}).get('REMOTE_ADDR')
        except Exception:
            return None

    @staticmethod
    def _extract_safe_headers(request) -> Dict[str, str]:
        """Extract safe headers from request."""
        try:
            meta = getattr(request, 'META', {})
            safe_headers = {}

            # Include commonly useful headers
            header_mappings = {
                'HTTP_HOST': 'host',
                'HTTP_REFERER': 'referer',
                'HTTP_ACCEPT_LANGUAGE': 'accept_language',
                'CONTENT_TYPE': 'content_type',
                'CONTENT_LENGTH': 'content_length',
            }

            for meta_key, header_key in header_mappings.items():
                if meta_key in meta:
                    safe_headers[header_key] = meta[meta_key]

            return safe_headers
        except Exception:
            return {}

    @staticmethod
    def enrich_bulk(evidence_queryset, context: Optional[Dict[str, Any]] = None) -> int:
        """
        Enrich multiple evidence instances.

        Args:
            evidence_queryset: QuerySet of evidence to enrich
            context: Context information for enrichment

        Returns:
            Number of evidence instances enriched
        """
        count = 0
        for evidence in evidence_queryset:
            try:
                EvidenceEnricher.enrich_evidence(evidence, context)
                count += 1
            except Exception as e:
                # Log error but continue processing
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to enrich evidence {evidence.id}: {e}")

        return count

    @staticmethod
    def validate_metadata(evidence: Evidence) -> Dict[str, Any]:
        """
        Validate and analyze evidence metadata.

        Args:
            evidence: Evidence instance to validate

        Returns:
            Validation results
        """
        results = {
            'is_valid': True,
            'issues': [],
            'recommendations': [],
        }

        metadata = evidence.metadata or {}

        # Check for required fields
        required_fields = ['evidence_uuid', 'enriched_at']
        for field in required_fields:
            if field not in metadata:
                results['issues'].append(f"Missing required field: {field}")

        # Check file integrity
        if evidence.file and evidence.sha256:
            try:
                with open(evidence.file.path, 'rb') as f:
                    content = f.read()
                    calculated_hash = hashlib.sha256(content).hexdigest()
                    if calculated_hash != evidence.sha256:
                        results['issues'].append("File hash mismatch")
                        results['is_valid'] = False
            except Exception as e:
                results['issues'].append(f"File integrity check failed: {e}")
                results['is_valid'] = False

        # Check metadata consistency
        if evidence.kind == 'screenshot' and not metadata.get('screenshot_info'):
            results['recommendations'].append("Screenshot evidence should have screenshot_info metadata")

        if evidence.correlation_id and not metadata.get('correlation_info'):
            results['recommendations'].append("Correlated evidence should have correlation_info metadata")

        return results