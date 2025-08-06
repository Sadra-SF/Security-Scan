from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from schedules.models import Schedule


class Command(BaseCommand):
    help = "Recompute next_run_at for all enabled schedules."

    def handle(self, *args, **options):
        from schedules.tasks import compute_next_run  # lazy import

        now = timezone.now()
        qs = Schedule.objects.select_related("target").filter(enabled=True)
        total = qs.count()
        updated = 0
        for sch in qs.iterator():
            nxt = compute_next_run(sch, now)
            if nxt != sch.next_run_at:
                Schedule.objects.filter(pk=sch.pk).update(next_run_at=nxt)
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Processed={total} Updated={updated}"))