import re
import logging
from typing import List, Dict, Optional
from django.db import transaction
from .models import ComplianceMapping, ComplianceControl
from findings.models import Finding

logger = logging.getLogger(__name__)


class ComplianceMappingService:
    """Service for mapping findings to compliance controls."""

    @staticmethod
    def map_finding_to_controls(finding: Finding) -> List[ComplianceControl]:
        """
        Map a finding to relevant compliance controls based on mapping rules.

        Args:
            finding: The finding to map

        Returns:
            List of compliance controls that apply to this finding
        """
        applicable_controls = []
        mappings = ComplianceMapping.objects.filter(is_active=True)

        for mapping in mappings:
            if ComplianceMappingService._matches_finding(finding, mapping):
                applicable_controls.append(mapping.control)

        return list(set(applicable_controls))  # Remove duplicates

    @staticmethod
    def _matches_finding(finding: Finding, mapping: ComplianceMapping) -> bool:
        """
        Check if a finding matches a compliance mapping rule.

        Args:
            finding: The finding to check
            mapping: The mapping rule

        Returns:
            True if the finding matches the mapping
        """
        # Check finding type match
        if not ComplianceMappingService._matches_finding_type(finding, mapping.finding_type):
            return False

        # Check pattern match if specified
        if mapping.finding_pattern:
            if not ComplianceMappingService._matches_pattern(finding, mapping.finding_pattern):
                return False

        return True

    @staticmethod
    def _matches_finding_type(finding: Finding, finding_type: str) -> bool:
        """
        Check if finding matches the specified finding type.

        Args:
            finding: The finding
            finding_type: The expected finding type

        Returns:
            True if types match
        """
        # Extract finding type from metadata or title/description
        finding_type_from_metadata = finding.metadata.get('finding_type', '')
        if finding_type_from_metadata == finding_type:
            return True

        # Fallback: check title and description for keywords
        text_to_check = f"{finding.title} {finding.description}".lower()
        type_keywords = ComplianceMappingService._get_finding_type_keywords(finding_type)

        return any(keyword in text_to_check for keyword in type_keywords)

    @staticmethod
    def _get_finding_type_keywords(finding_type: str) -> List[str]:
        """Get keywords associated with a finding type."""
        keyword_map = {
            'sql_injection': ['sql injection', 'sqli', 'sql'],
            'xss': ['cross-site scripting', 'xss', 'scripting'],
            'csrf': ['cross-site request forgery', 'csrf', 'forgery'],
            'weak_authentication': ['weak authentication', 'weak auth', 'authentication'],
            'weak_encryption': ['weak encryption', 'encryption', 'ssl', 'tls'],
            'information_disclosure': ['information disclosure', 'info disclosure', 'leak'],
            'broken_access_control': ['broken access control', 'access control', 'authorization'],
            'security_misconfiguration': ['security misconfiguration', 'misconfiguration', 'config'],
            'vulnerable_components': ['vulnerable components', 'outdated', 'vulnerable'],
            'insufficient_logging': ['insufficient logging', 'logging', 'audit'],
        }
        return keyword_map.get(finding_type, [finding_type.replace('_', ' ')])

    @staticmethod
    def _matches_pattern(finding: Finding, pattern: str) -> bool:
        """
        Check if finding matches a regex pattern.

        Args:
            finding: The finding
            pattern: Regex pattern to match against

        Returns:
            True if pattern matches
        """
        try:
            text_to_check = f"{finding.title} {finding.description}"
            return bool(re.search(pattern, text_to_check, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return False

    @staticmethod
    @transaction.atomic
    def update_finding_compliance_controls(finding: Finding) -> None:
        """
        Update the compliance controls for a finding.

        Args:
            finding: The finding to update
        """
        applicable_controls = ComplianceMappingService.map_finding_to_controls(finding)
        finding.compliance_controls.set(applicable_controls)
        finding.save()

        if applicable_controls:
            logger.info(f"Mapped finding {finding.id} to {len(applicable_controls)} compliance controls")
        else:
            logger.debug(f"No compliance controls found for finding {finding.id}")

    @staticmethod
    @transaction.atomic
    def bulk_update_findings_compliance_controls(findings: List[Finding]) -> Dict[str, int]:
        """
        Bulk update compliance controls for multiple findings.

        Args:
            findings: List of findings to update

        Returns:
            Dictionary with update statistics
        """
        stats = {'processed': 0, 'mapped': 0, 'unmapped': 0}

        for finding in findings:
            ComplianceMappingService.update_finding_compliance_controls(finding)
            stats['processed'] += 1

            if finding.compliance_controls.exists():
                stats['mapped'] += 1
            else:
                stats['unmapped'] += 1

        logger.info(f"Bulk compliance mapping completed: {stats}")
        return stats

    @staticmethod
    def get_compliance_summary_for_findings(findings: List[Finding]) -> Dict:
        """
        Get compliance summary for a list of findings.

        Args:
            findings: List of findings

        Returns:
            Dictionary with compliance summary
        """
        summary = {
            'total_findings': len(findings),
            'mapped_findings': 0,
            'unmapped_findings': 0,
            'frameworks': {},
            'controls': {},
        }

        for finding in findings:
            controls = finding.compliance_controls.all()
            if controls:
                summary['mapped_findings'] += 1

                for control in controls:
                    framework_name = control.framework.name
                    control_id = control.control_id

                    if framework_name not in summary['frameworks']:
                        summary['frameworks'][framework_name] = 0
                    summary['frameworks'][framework_name] += 1

                    if control_id not in summary['controls']:
                        summary['controls'][control_id] = 0
                    summary['controls'][control_id] += 1
            else:
                summary['unmapped_findings'] += 1

        return summary