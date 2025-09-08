import logging
from typing import Optional
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ComplianceAssessment
from notifications.tasks import dispatch_event

logger = logging.getLogger(__name__)


class ComplianceNotificationService:
    """Service for sending compliance-related notifications."""

    @staticmethod
    def notify_assessment_completed(assessment: ComplianceAssessment) -> None:
        """
        Send notification when a compliance assessment is completed.

        Args:
            assessment: The completed compliance assessment
        """
        try:
            # Determine notification event type based on compliance status
            if assessment.compliance_status in ['non_compliant', 'partially_compliant']:
                event_type = 'compliance_violation'
                title = f"Compliance Violation: {assessment.framework.name}"
                message = f"Compliance assessment for {assessment.target.name} shows {assessment.get_compliance_status_display().lower()} status."
            else:
                event_type = 'compliance_assessment_completed'
                title = f"Compliance Assessment Completed: {assessment.framework.name}"
                message = f"Compliance assessment for {assessment.target.name} completed with {assessment.get_compliance_status_display().lower()} status."

            # Add assessment details
            message += f"\n\nFramework: {assessment.framework.name}"
            message += f"\nTarget: {assessment.target.name}"
            message += f"\nOverall Score: {assessment.overall_score}%"
            message += f"\nStatus: {assessment.get_compliance_status_display()}"

            # Add findings summary if available
            if assessment.findings_count:
                findings_summary = []
                for severity, count in assessment.findings_count.items():
                    if count > 0:
                        findings_summary.append(f"{count} {severity}")
                if findings_summary:
                    message += f"\nFindings: {', '.join(findings_summary)}"

            # For now, log the notification - in a real implementation,
            # you would integrate with the notification system
            logger.info(f"Compliance notification: {title} - {message}")

            logger.info(f"Sent {event_type} notification for assessment {assessment.id}")

        except Exception as e:
            logger.error(f"Failed to send compliance notification for assessment {assessment.id}: {e}")

    @staticmethod
    def notify_critical_compliance_violation(assessment: ComplianceAssessment, critical_findings: list) -> None:
        """
        Send urgent notification for critical compliance violations.

        Args:
            assessment: The compliance assessment
            critical_findings: List of critical findings
        """
        try:
            title = f"CRITICAL: Compliance Violation - {assessment.framework.name}"
            message = f"Critical compliance violations detected for {assessment.target.name}!\n\n"

            message += f"Framework: {assessment.framework.name}\n"
            message += f"Target: {assessment.target.name}\n"
            message += f"Critical Findings: {len(critical_findings)}\n\n"

            # List critical findings
            for i, finding in enumerate(critical_findings[:5], 1):  # Limit to first 5
                message += f"{i}. {finding.title} (Severity: {finding.severity})\n"

            if len(critical_findings) > 5:
                message += f"... and {len(critical_findings) - 5} more critical findings\n"

            # For now, log the critical notification
            logger.warning(f"Critical compliance notification: {title} - {message}")

            logger.info(f"Sent critical compliance violation notification for assessment {assessment.id}")

        except Exception as e:
            logger.error(f"Failed to send critical compliance notification for assessment {assessment.id}: {e}")


@receiver(post_save, sender=ComplianceAssessment)
def notify_on_assessment_completion(sender, instance, created, **kwargs):
    """
    Automatically send notifications when compliance assessments are completed.
    """
    # Only notify on updates (not creation) and when assessment is completed
    if not created and instance.assessment_status == 'completed':
        ComplianceNotificationService.notify_assessment_completed(instance)

        # Check for critical violations
        critical_count = instance.findings_count.get('critical', 0)
        if critical_count > 0:
            # Get critical findings (this would need to be implemented)
            # For now, just pass the count
            ComplianceNotificationService.notify_critical_compliance_violation(
                instance, list(range(critical_count))  # Placeholder
            )