from django.contrib import admin
from .models import Scan


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target",
        "scanner",
        "type",
        "status",
        "started_at",
        "finished_at",
        "created_at",
    )
    search_fields = ("id", "target__name", "target__slug", "scanner")
    list_filter = ("status", "type", "scanner", "created_at", "started_at")
    ordering = ("-started_at", "-created_at")