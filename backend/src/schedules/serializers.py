from django.utils import timezone
from rest_framework import serializers
from .models import Schedule

# Avoid circular import at module import; we'll import compute_next_run lazily


def _validate_cron_field(value: str, name: str) -> None:
    # Minimal validation: allow "*", "*/N", "N", "N,N2", ranges "A-B"
    # We don't fully parse cron, just sanity-check to avoid obvious bad inputs.
    allowed_chars = set("0123456789*,/-")
    if not isinstance(value, str) or not value:
        raise serializers.ValidationError({name: "Must be a non-empty string"})
    if any(ch not in allowed_chars for ch in value):
        raise serializers.ValidationError({name: "Contains invalid characters"})
    # basic patterns
    if value.startswith("*/"):
        try:
            int(value[2:])
        except Exception:
            raise serializers.ValidationError({name: "Invalid step value"})
    # else accept other simple forms as-is


def _has_any_cron_fields(attrs) -> bool:
    return any(attrs.get(k) not in (None, "",) for k in ("minute", "hour", "day_of_week", "day_of_month", "month_of_year"))


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = (
            "id",
            "target",
            "minute",
            "hour",
            "day_of_week",
            "day_of_month",
            "month_of_year",
            "scanner",
            "config",
            "enabled",
            "last_run_at",
            "next_run_at",
            "timezone_name",
            "window_start",
            "window_end",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("last_run_at", "created_at", "updated_at")

    def validate(self, attrs):
        data = super().validate(attrs)
        # Validate cron-like fields if provided
        for fld in ("minute", "hour", "day_of_week", "day_of_month", "month_of_year"):
            if fld in attrs and attrs.get(fld) is not None:
                _validate_cron_field(attrs.get(fld), fld)

        # Validate cadence preset if given in config
        cfg = (attrs.get("config") if "config" in attrs else getattr(self.instance, "config", {}) or {}) or {}
        cadence = (cfg.get("cadence") or cfg.get("schedule") or "").lower() if isinstance(cfg, dict) else ""
        if cadence and cadence not in ("hourly", "daily", "weekly"):
            raise serializers.ValidationError({"config": "Unsupported cadence. Use hourly/daily/weekly or omit."})

        # Validate timezone_name if provided
        if "timezone_name" in attrs and attrs.get("timezone_name"):
            tz_name = attrs["timezone_name"]
            try:
                import pytz
                pytz.timezone(tz_name)
            except Exception:
                raise serializers.ValidationError({"timezone_name": f"Invalid timezone: {tz_name}"})

        # Validate window_start and window_end format if provided
        for field in ("window_start", "window_end"):
            if field in attrs and attrs.get(field):
                value = attrs[field]
                if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
                    raise serializers.ValidationError({field: "Must be in HH:MM format"})
                try:
                    hh, mm = value.split(":")
                    hh, mm = int(hh), int(mm)
                    if not (0 <= hh <= 23) or not (0 <= mm <= 59):
                        raise serializers.ValidationError({field: "Invalid time values"})
                except Exception:
                    raise serializers.ValidationError({field: "Must be in HH:MM format"})

        # Ensure at least something schedules it: either cadence or cron fields
        if not cadence and not _has_any_cron_fields({**getattr(self.instance, "__dict__", {}), **attrs}):
            # If nothing set, default to minute="*"
            attrs.setdefault("minute", "*")

        return data

    def _compute_initial_next(self, schedule: Schedule):
        # lazy import to avoid circulars
        from schedules.tasks import compute_next_run
        now = timezone.now()
        nxt = compute_next_run(schedule, now)
        return nxt

    def create(self, validated_data):
        schedule = super().create(validated_data)
        # compute initial next_run_at if enabled and not provided
        if schedule.enabled and not schedule.next_run_at:
            nxt = self._compute_initial_next(schedule)
            schedule.next_run_at = nxt
            schedule.save(update_fields=["next_run_at", "updated_at"])
        return schedule

    def update(self, instance, validated_data):
        schedule = super().update(instance, validated_data)
        # recompute next_run_at when schedule changes and enabled
        if schedule.enabled:
            nxt = self._compute_initial_next(schedule)
            schedule.next_run_at = nxt
            schedule.save(update_fields=["next_run_at", "updated_at"])
        return schedule