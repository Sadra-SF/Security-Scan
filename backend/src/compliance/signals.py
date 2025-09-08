import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from findings.models import Finding
from .services import ComplianceMappingService

# Thread-local storage to prevent recursion
_local = threading.local()


@receiver(post_save, sender=Finding)
def map_finding_to_compliance_controls(sender, instance, created, **kwargs):
    """
    Automatically map findings to compliance controls when they're created or updated.
    """
    # Prevent recursion: if we're already updating compliance controls, skip
    if getattr(_local, 'updating_compliance', False):
        return

    try:
        _local.updating_compliance = True
        ComplianceMappingService.update_finding_compliance_controls(instance)
    except Exception as e:
        # Log the error but don't break the finding save process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to map finding {instance.id} to compliance controls: {e}")
    finally:
        _local.updating_compliance = False


# Connect the signal
post_save.connect(map_finding_to_compliance_controls, sender=Finding)