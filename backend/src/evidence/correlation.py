"""
Evidence correlation utilities for enhanced vulnerability analysis.
"""
import logging
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from .models import Evidence
from findings.models import Finding

logger = logging.getLogger(__name__)


class EvidenceCorrelator:
    """Advanced evidence correlation and analysis utilities."""

    @staticmethod
    def correlate_by_url(evidence_list: List[Evidence], url_field: str = "url") -> Dict[str, List[Evidence]]:
        """
        Correlate evidence by URL patterns.

        Args:
            evidence_list: List of evidence to correlate
            url_field: Metadata field containing URL

        Returns:
            Dictionary mapping URLs to lists of related evidence
        """
        url_groups = defaultdict(list)

        for evidence in evidence_list:
            url = evidence.metadata.get(url_field)
            if url:
                # Normalize URL for better correlation
                normalized_url = EvidenceCorrelator._normalize_url(url)
                url_groups[normalized_url].append(evidence)

        return dict(url_groups)

    @staticmethod
    def correlate_by_vulnerability_type(evidence_list: List[Evidence]) -> Dict[str, List[Evidence]]:
        """
        Correlate evidence by vulnerability type.

        Args:
            evidence_list: List of evidence to correlate

        Returns:
            Dictionary mapping vulnerability types to evidence lists
        """
        vuln_groups = defaultdict(list)

        for evidence in evidence_list:
            vuln_type = (
                evidence.metadata.get("vulnerability_type") or
                evidence.metadata.get("category") or
                "unknown"
            )
            vuln_groups[vuln_type].append(evidence)

        return dict(vuln_groups)

    @staticmethod
    def find_evidence_chains(evidence_list: List[Evidence]) -> List[List[Evidence]]:
        """
        Find chains of related evidence based on correlation patterns.

        Args:
            evidence_list: List of evidence to analyze

        Returns:
            List of evidence chains
        """
        chains = []

        # Group by correlation_id first
        correlation_groups = defaultdict(list)
        for evidence in evidence_list:
            if evidence.correlation_id:
                correlation_groups[evidence.correlation_id].append(evidence)

        # Add correlation groups as chains
        for group in correlation_groups.values():
            if len(group) > 1:
                chains.append(sorted(group, key=lambda e: e.created_at))

        # Find additional chains based on metadata patterns
        metadata_chains = EvidenceCorrelator._find_metadata_chains(evidence_list)
        chains.extend(metadata_chains)

        return chains

    @staticmethod
    def analyze_evidence_patterns(finding: Finding) -> Dict[str, Any]:
        """
        Analyze evidence patterns for a finding.

        Args:
            finding: Finding to analyze

        Returns:
            Analysis results
        """
        from .models import Evidence
        evidence_list = list(Evidence.objects.filter(finding=finding))
        if not evidence_list:
            return {"patterns": [], "insights": []}

        patterns = []
        insights = []

        # Analyze evidence types
        evidence_types = {}
        for evidence in evidence_list:
            evidence_types[evidence.kind] = evidence_types.get(evidence.kind, 0) + 1

        patterns.append({
            "type": "evidence_types",
            "data": evidence_types,
            "description": f"Mixed evidence types: {', '.join(evidence_types.keys())}"
        })

        # Analyze temporal patterns
        if len(evidence_list) > 1:
            timestamps = [e.created_at for e in evidence_list]
            time_span = max(timestamps) - min(timestamps)
            patterns.append({
                "type": "temporal",
                "data": {
                    "span_seconds": time_span.total_seconds(),
                    "evidence_count": len(evidence_list)
                },
                "description": f"Evidence collected over {time_span.total_seconds():.1f} seconds"
            })

        # Analyze correlation patterns
        correlated_count = sum(1 for e in evidence_list if e.correlation_id)
        if correlated_count > 0:
            insights.append(f"{correlated_count} pieces of evidence are correlated")

        # Analyze file sizes
        total_size = sum(e.size or 0 for e in evidence_list)
        if total_size > 0:
            patterns.append({
                "type": "size_analysis",
                "data": {"total_size": total_size},
                "description": f"Total evidence size: {total_size} bytes"
            })

        return {
            "patterns": patterns,
            "insights": insights,
            "evidence_count": len(evidence_list),
            "evidence_types": list(evidence_types.keys())
        }

    @staticmethod
    def suggest_correlations(evidence_list: List[Evidence]) -> List[Dict[str, Any]]:
        """
        Suggest correlations between evidence based on patterns.

        Args:
            evidence_list: List of evidence to analyze

        Returns:
            List of correlation suggestions
        """
        suggestions = []

        # Suggest URL-based correlations
        url_groups = EvidenceCorrelator.correlate_by_url(evidence_list)
        for url, group in url_groups.items():
            if len(group) > 1:
                suggestions.append({
                    "type": "url_correlation",
                    "evidence_ids": [str(e.id) for e in group],
                    "reason": f"Multiple evidence items for URL: {url}",
                    "confidence": "high"
                })

        # Suggest vulnerability type correlations
        vuln_groups = EvidenceCorrelator.correlate_by_vulnerability_type(evidence_list)
        for vuln_type, group in vuln_groups.items():
            if len(group) > 1:
                suggestions.append({
                    "type": "vulnerability_correlation",
                    "evidence_ids": [str(e.id) for e in group],
                    "reason": f"Related to vulnerability type: {vuln_type}",
                    "confidence": "medium"
                })

        # Suggest temporal correlations
        if len(evidence_list) > 2:
            sorted_evidence = sorted(evidence_list, key=lambda e: e.created_at)
            time_diffs = []
            for i in range(1, len(sorted_evidence)):
                diff = (sorted_evidence[i].created_at - sorted_evidence[i-1].created_at).total_seconds()
                time_diffs.append(diff)

            avg_diff = sum(time_diffs) / len(time_diffs) if time_diffs else 0
            if avg_diff < 60:  # Within 1 minute
                suggestions.append({
                    "type": "temporal_correlation",
                    "evidence_ids": [str(e.id) for e in sorted_evidence],
                    "reason": f"Evidence collected in rapid succession (avg {avg_diff:.1f}s apart)",
                    "confidence": "medium"
                })

        return suggestions

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for better correlation."""
        if not url:
            return ""

        # Remove common tracking parameters
        from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
        try:
            parsed = urlparse(url)
            query_params = parse_qsl(parsed.query)

            # Remove common tracking/noise parameters
            filtered_params = [
                (k, v) for k, v in query_params
                if k.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', '_ga', '_gid']
            ]

            # Reconstruct URL
            new_query = urlencode(filtered_params, doseq=True)
            normalized = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

            return normalized
        except Exception:
            return url

    @staticmethod
    def _find_metadata_chains(evidence_list: List[Evidence]) -> List[List[Evidence]]:
        """Find evidence chains based on metadata patterns."""
        chains = []

        # Group by common metadata patterns
        pattern_groups = defaultdict(list)

        for evidence in evidence_list:
            # Create pattern key from relevant metadata
            pattern_key = EvidenceCorrelator._create_pattern_key(evidence)
            if pattern_key:
                pattern_groups[pattern_key].append(evidence)

        # Convert groups to chains
        for group in pattern_groups.values():
            if len(group) > 1:
                chains.append(sorted(group, key=lambda e: e.created_at))

        return chains

    @staticmethod
    def _create_pattern_key(evidence: Evidence) -> Optional[str]:
        """Create a pattern key for evidence correlation."""
        metadata = evidence.metadata

        # Use URL and vulnerability type as primary pattern
        url = metadata.get("url") or metadata.get("target_url")
        vuln_type = metadata.get("vulnerability_type") or metadata.get("category")

        if url and vuln_type:
            return f"{EvidenceCorrelator._normalize_url(url)}:{vuln_type}"

        # Fallback to just URL
        if url:
            return EvidenceCorrelator._normalize_url(url)

        # Fallback to correlation_id if available
        if evidence.correlation_id:
            return f"correlation:{evidence.correlation_id}"

        return None


def auto_correlate_evidence(finding: Finding) -> int:
    """
    Automatically correlate evidence for a finding based on patterns.

    Args:
        finding: Finding whose evidence should be correlated

    Returns:
        Number of correlation groups created
    """
    from .models import Evidence
    evidence_list = list(Evidence.objects.filter(finding=finding))
    if len(evidence_list) < 2:
        return 0

    correlator = EvidenceCorrelator()
    suggestions = correlator.suggest_correlations(evidence_list)

    correlation_count = 0

    for suggestion in suggestions:
        if suggestion["confidence"] in ["high", "medium"]:
            try:
                Evidence.correlate_evidence(
                    evidence_ids=suggestion["evidence_ids"],
                    correlation_type=suggestion["type"]
                )
                correlation_count += 1
                logger.info(f"Auto-correlated evidence: {suggestion['reason']}")
            except Exception as e:
                logger.warning(f"Failed to auto-correlate evidence: {e}")

    return correlation_count