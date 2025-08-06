from django.contrib import admin
from .models import Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target",
        "scanner",
        "enabled",
        "minute",
        "hour",
        "day_of_week",
        "day_of_month",
        "month_of_year",
        "next_run_at",
        "last_run_at",
        "created_at",
    )
    search_fields = ("id", "target__name", "target__slug", "scanner")
    list_filter = ("enabled", "scanner", "created_at", "next_run_at", "target__project__organization")
    ordering = ("-next_run_at", "-created_at")