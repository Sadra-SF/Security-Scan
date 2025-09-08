import logging
from typing import Dict, List, Optional, Union
from django.db.models import QuerySet
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Count, Q
from .models import ComplianceFramework, ComplianceControl, ComplianceAssessment
from findings.models import Finding
from .services import ComplianceMappingService

logger = logging.getLogger(__name__)


class ComplianceAssessmentService:
    """Service for assessing compliance status based on findings."""

    @staticmethod
    @transaction.atomic
    def assess_target_compliance(target, framework: ComplianceFramework, project=None) -> ComplianceAssessment:
        """
        Assess compliance for a target against a specific framework.

        Args:
            target: The target to assess
            framework: The compliance framework
            project: Optional project context

        Returns:
            Updated or created ComplianceAssessment
        """
        # Get or create assessment
        assessment, created = ComplianceAssessment.objects.get_or_create(
            framework=framework,
            target=target,
            defaults={'project': project}
        )

        # Update assessment status
        assessment.assessment_status = ComplianceAssessment.AssessmentStatus.IN_PROGRESS
        assessment.save()

        try:
            # Get all findings for the target
            findings = Finding.objects.filter(target=target)

            # Calculate compliance metrics
            metrics = ComplianceAssessmentService._calculate_compliance_metrics(findings, framework)

            # Update assessment with results
            assessment.assessment_status = ComplianceAssessment.AssessmentStatus.COMPLETED
            assessment.compliance_status = metrics['compliance_status']
            assessment.overall_score = metrics['overall_score']
            assessment.control_scores = metrics['control_scores']
            assessment.findings_count = metrics['findings_count']
            assessment.last_assessed_at = datetime.now()

            # Set next assessment (e.g., weekly)
            assessment.next_assessment_at = datetime.now() + timedelta(days=7)

            assessment.save()

            logger.info(f"Compliance assessment completed for {target} against {framework.name}: {assessment.compliance_status}")

        except Exception as e:
            assessment.assessment_status = ComplianceAssessment.AssessmentStatus.FAILED
            assessment.save()
            logger.error(f"Compliance assessment failed for {target} against {framework.name}: {e}")
            raise

        return assessment

    @staticmethod
    def _calculate_compliance_metrics(findings: Union[QuerySet[Finding], List[Finding]], framework: ComplianceFramework) -> Dict:
        """
        Calculate compliance metrics for findings against a framework.

        Args:
            findings: List of findings
            framework: The compliance framework

        Returns:
            Dictionary with compliance metrics
        """
        # Get all controls for the framework
        controls = ComplianceControl.objects.filter(framework=framework, is_active=True)

        control_scores = {}
        findings_count = {'info': 0, 'low': 0, 'medium': 0, 'high': 0, 'critical': 0}

        total_score = 0
        total_controls = 0

        for control in controls:
            control_findings = ComplianceAssessmentService._get_findings_for_control(findings, control)
            score = ComplianceAssessmentService._calculate_control_score(control, control_findings)

            control_scores[control.control_id] = score
            total_score += score
            total_controls += 1

            # Count findings by severity
            for finding in control_findings:
                findings_count[finding.severity] += 1

        # Calculate overall score
        overall_score = total_score / total_controls if total_controls > 0 else 100

        # Determine compliance status
        compliance_status = ComplianceAssessmentService._determine_compliance_status(
            overall_score, findings_count
        )

        return {
            'overall_score': overall_score,
            'control_scores': control_scores,
            'findings_count': findings_count,
            'compliance_status': compliance_status,
        }

    @staticmethod
    def _get_findings_for_control(findings: Union[QuerySet[Finding], List[Finding]], control: ComplianceControl) -> List[Finding]:
        """
        Get findings that are relevant to a specific control.

        Args:
            findings: All findings
            control: The compliance control

        Returns:
            List of findings relevant to the control
        """
        # Check direct mapping first
        direct_mapped = [f for f in findings if control in f.compliance_controls.all()]

        if direct_mapped:
            return direct_mapped

        # Fallback: use mapping service to find applicable findings
        applicable_findings = []
        for finding in findings:
            try:
                if control in ComplianceMappingService.map_finding_to_controls(finding):
                    applicable_findings.append(finding)
            except Exception as e:
                logger.warning(f"Error mapping finding {finding.id} to controls: {e}")
                continue

        return applicable_findings

    @staticmethod
    def _calculate_control_score(control: ComplianceControl, findings: List[Finding]) -> int:
        """
        Calculate compliance score for a control based on its findings.

        Args:
            control: The compliance control
            findings: Findings relevant to this control

        Returns:
            Score from 0-100 (100 = compliant)
        """
        if not findings:
            return 100  # No findings = compliant

        # Weight findings by severity
        severity_weights = {
            'info': 1,
            'low': 2,
            'medium': 5,
            'high': 10,
            'critical': 20
        }

        total_weight = 0
        for finding in findings:
            # Only count open/acknowledged findings
            if finding.status in ['open', 'acknowledged']:
                total_weight += severity_weights.get(finding.severity, 1)

        # Calculate score based on weighted findings
        # More weight = lower score
        if total_weight == 0:
            return 100
        elif total_weight <= 5:
            return 90
        elif total_weight <= 15:
            return 70
        elif total_weight <= 30:
            return 50
        else:
            return 20

    @staticmethod
    def _determine_compliance_status(overall_score: float, findings_count: Dict) -> str:
        """
        Determine overall compliance status.

        Args:
            overall_score: Overall compliance score (0-100)
            findings_count: Count of findings by severity

        Returns:
            Compliance status
        """
        # Check for critical findings
        if findings_count.get('critical', 0) > 0:
            return ComplianceAssessment.ComplianceStatus.NON_COMPLIANT

        # Check for high findings
        if findings_count.get('high', 0) > 2:
            return ComplianceAssessment.ComplianceStatus.NON_COMPLIANT

        # Check overall score
        if overall_score >= 90:
            return ComplianceAssessment.ComplianceStatus.COMPLIANT
        elif overall_score >= 70:
            return ComplianceAssessment.ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return ComplianceAssessment.ComplianceStatus.NON_COMPLIANT

    @staticmethod
    def get_compliance_report(target, framework: ComplianceFramework) -> Dict:
        """
        Generate a detailed compliance report.

        Args:
            target: The target
            framework: The compliance framework

        Returns:
            Dictionary with compliance report data
        """
        try:
            assessment = ComplianceAssessment.objects.get(
                framework=framework,
                target=target
            )
        except ComplianceAssessment.DoesNotExist:
            return {'error': 'No assessment found'}

        findings = Finding.objects.filter(target=target)
        controls = ComplianceControl.objects.filter(framework=framework, is_active=True)

        report = {
            'framework': {
                'name': framework.name,
                'type': framework.get_type_display(),
                'version': framework.version,
            },
            'assessment': {
                'status': assessment.get_assessment_status_display(),
                'compliance_status': assessment.get_compliance_status_display(),
                'overall_score': assessment.overall_score,
                'last_assessed': assessment.last_assessed_at,
                'next_assessment': assessment.next_assessment_at,
            },
            'findings_summary': assessment.findings_count,
            'controls': [],
        }

        for control in controls:
            control_findings = ComplianceAssessmentService._get_findings_for_control(findings, control)
            control_data = {
                'id': control.control_id,
                'title': control.title,
                'severity': control.severity,
                'score': assessment.control_scores.get(control.control_id, 100),
                'findings_count': len(control_findings),
                'findings': [
                    {
                        'id': str(f.id),
                        'title': f.title,
                        'severity': f.severity,
                        'status': f.status,
                    } for f in control_findings[:5]  # Limit to first 5 findings
                ]
            }
            report['controls'].append(control_data)

        return report

    @staticmethod
    def bulk_assess_compliance(targets: List, framework: ComplianceFramework, project=None) -> Dict[str, int]:
        """
        Bulk assess compliance for multiple targets.

        Args:
            targets: List of targets to assess
            framework: The compliance framework
            project: Optional project context

        Returns:
            Dictionary with assessment statistics
        """
        stats = {'processed': 0, 'successful': 0, 'failed': 0}

        for target in targets:
            try:
                ComplianceAssessmentService.assess_target_compliance(target, framework, project)
                stats['successful'] += 1
            except Exception as e:
                logger.error(f"Failed to assess {target}: {e}")
                stats['failed'] += 1
            finally:
                stats['processed'] += 1

        logger.info(f"Bulk compliance assessment completed: {stats}")
        return stats