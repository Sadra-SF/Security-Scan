from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Schedule


@receiver(post_save, sender=Schedule)
def ensure_next_run(sender, instance: Schedule, created: bool, **kwargs):
    """
    Recalculate next_run_at if missing after save and schedule is enabled.
    """
    if not instance.enabled:
        return
    if instance.next_run_at:
        return
    try:
        from schedules.tasks import compute_next_run

        nxt = compute_next_run(instance, timezone.now())
        if nxt:
            # Avoid recursion: update only the fields needed
            sender.objects.filter(pk=instance.pk).update(next_run_at=nxt)
    except Exception:
        # Silent fail; serializer/create path should usually set it
        pass