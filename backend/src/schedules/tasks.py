from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from schedules.models import Schedule
from scans.models import Scan
from scans.tasks import start_scan

logger = logging.getLogger(__name__)


def _now_tz():
    return timezone.now()


def _in_maintenance_window(schedule: Schedule, dt) -> bool:
    """
    Honor maintenance windows if available.
    Priority: schedule fields window_start/window_end/timezone if they exist,
    otherwise consult schedule.target.settings["window_start"/"window_end"/"timezone"].
    window_* are "HH:MM" 24h strings; timezone is IANA tz.
    If no window configured, return False (not in maintenance).
    """
    try:
        # attempt model-level attributes
        window_start = getattr(schedule, "window_start", None)
        window_end = getattr(schedule, "window_end", None)
        tz_name = getattr(schedule, "timezone_name", None)
    except Exception:
        window_start = window_end = tz_name = None

    if not window_start and not window_end:
        # look into target.settings
        stg = (getattr(schedule.target, "settings", {}) or {})
        window_start = stg.get("window_start")
        window_end = stg.get("window_end")
        tz_name = tz_name or stg.get("timezone")

    if not window_start and not window_end:
        return False

    # Convert dt to provided tz if present
    local_dt = dt
    if tz_name:
        try:
            import pytz

            tz = pytz.timezone(tz_name)
            local_dt = dt.astimezone(tz)
        except Exception:
            pass  # fallback to dt as-is

    def _parse_hhmm(s: str):
        try:
            hh, mm = s.split(":")
            return int(hh), int(mm)
        except Exception:
            return None

    ws = _parse_hhmm(window_start) if window_start else None
    we = _parse_hhmm(window_end) if window_end else None
    if not ws and not we:
        return False

    # build today's window
    start_minutes = ws[0] * 60 + ws[1] if ws else None
    end_minutes = we[0] * 60 + we[1] if we else None
    cur_minutes = local_dt.hour * 60 + local_dt.minute

    if start_minutes is not None and end_minutes is not None:
        if start_minutes <= end_minutes:
            return start_minutes <= cur_minutes < end_minutes
        else:
            # wraps around midnight
            return cur_minutes >= start_minutes or cur_minutes < end_minutes
    if start_minutes is not None:
        # Block starting from start to end of day
        return cur_minutes >= start_minutes
    if end_minutes is not None:
        # Block from start of day to end
        return cur_minutes < end_minutes
    return False


def compute_next_run(schedule: Schedule, from_dt) -> Optional[timezone.datetime]:
    """
    Compute next run using:
    1) croniter if available and cron-like fields
    2) 'cadence' preset in schedule.config: hourly/daily/weekly
    3) fallback to simple parsing of minute/hour with */N minutes support
    Returns timezone-aware datetime.
    """
    # 1) Try croniter
    minute = schedule.minute or "*"
    hour = schedule.hour or "*"
    day_of_week = schedule.day_of_week or "*"
    day_of_month = schedule.day_of_month or "*"
    month_of_year = schedule.month_of_year or "*"
    expr = f"{minute} {hour} {day_of_month} {month_of_year} {day_of_week}"
    try:
        from croniter import croniter  # type: ignore

        it = croniter(expr, from_dt)
        nxt = it.get_next(timezone.datetime)
        if timezone.is_naive(nxt):
            nxt = timezone.make_aware(nxt, timezone=from_dt.tzinfo)
        return nxt
    except Exception:
        pass

    # 2) cadence preset in config
    cadence = None
    try:
        cfg = schedule.config or {}
        cadence = (cfg.get("cadence") or cfg.get("schedule") or "").lower()
    except Exception:
        cadence = None

    if cadence == "hourly":
        return from_dt + timedelta(hours=1)
    if cadence == "daily":
        return from_dt + timedelta(days=1)
    if cadence == "weekly":
        return from_dt + timedelta(weeks=1)

    # 3) very small fallback: support */N in minute only, else default 1 hour
    try:
        if minute.startswith("*/"):
            n = int(minute[2:])
            return (from_dt.replace(second=0, microsecond=0) + timedelta(minutes=n))
    except Exception:
        pass

    return from_dt + timedelta(hours=1)


def _lock_key(schedule_id: str, minute_bucket: str) -> str:
    return f"schedule:{schedule_id}:{minute_bucket}"


def _minute_bucket(dt) -> str:
    dt = dt.replace(second=0, microsecond=0)
    return dt.strftime("%Y%m%d%H%M")


def _acquire_lock(schedule_id: str, now_dt) -> bool:
    """
    Use Django cache add (NX) for a short TTL lock. If cache unsupported, fall back later logic.
    """
    try:
        key = _lock_key(str(schedule_id), _minute_bucket(now_dt))
        # TTL: 70 seconds to cover clock skews
        return cache.add(key, "1", timeout=70)
    except Exception:
        return True  # proceed but rely on last_run_at minute guard


@shared_task(name="schedules.tasks.enqueue_due_scans")
def enqueue_due_scans() -> int:
    """
    Beat-driven task:
    - Query enabled schedules due at or before now
    - Respect maintenance windows
    - Idempotent enqueue using cache lock and minute-level guard on last_run_at
    - Create Scan row and enqueue scans.tasks.start_scan
    - Update last_run_at and next_run_at
    - Store a minimal metric 'schedules:last_enqueue_run_at' in cache
    """
    now = _now_tz()
    due = (
        Schedule.objects.select_related("target")
        .filter(enabled=True, next_run_at__isnull=False, next_run_at__lte=now)
        .order_by("next_run_at")
    )
    processed = 0

    for sch in due:
        # idempotency guard: if last_run_at exists in the same minute bucket, skip
        if sch.last_run_at:
            if _minute_bucket(sch.last_run_at) == _minute_bucket(now):
                continue

        # maintenance window check
        try:
            if _in_maintenance_window(sch, now):
                # push next_run ahead by minute to re-check soon
                nxt = compute_next_run(sch, now)
                with transaction.atomic():
                    sch.next_run_at = nxt or (now + timedelta(minutes=5))
                    sch.save(update_fields=["next_run_at", "updated_at"])
                continue
        except Exception as e:
            logger.warning("maintenance window check failed schedule=%s: %s", sch.id, e)

        # acquire cache lock
        if not _acquire_lock(str(sch.id), now):
            continue

        # Create Scan and enqueue
        try:
            with transaction.atomic():
                scan = Scan.objects.create(
                    target=sch.target,
                    scanner=sch.scanner,
                    type=Scan.ScanType.SCHEDULED,
                    status=Scan.Status.PENDING,
                    config=sch.config or {},
                )
                # enqueue start_scan
                start_scan.delay(str(scan.id))

                # update schedule run times
                sch.last_run_at = now
                next_dt = compute_next_run(sch, now)
                sch.next_run_at = next_dt
                sch.save(update_fields=["last_run_at", "next_run_at", "updated_at"])

                processed += 1
        except Exception as e:
            logger.exception("enqueue_due_scans failed for schedule=%s: %s", sch.id, e)
            # try to nudge next_run_at to avoid hot-loop
            try:
                with transaction.atomic():
                    sch.next_run_at = (sch.next_run_at or now) + timedelta(minutes=1)
                    sch.save(update_fields=["next_run_at", "updated_at"])
            except Exception:
                pass

    # minimal metric
    try:
        cache.set("schedules:last_enqueue_run_at", now.isoformat(), timeout=None)
    except Exception:
        pass

    logger.info("enqueue_due_scans processed=%s", processed)
    return processed