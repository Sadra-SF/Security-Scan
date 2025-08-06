from django.contrib import admin
from .models import Finding


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "target",
        "severity",
        "status",
        "last_seen_at",
        "created_at",
        "id",
    )
    search_fields = (
        "title",
        "id",
        "target__name",
        "target__slug",
    )
    list_filter = (
        "severity",
        "status",
        "created_at",
        "last_seen_at",
        "target__project__organization",
    )
    ordering = ("-last_seen_at", "-created_at")