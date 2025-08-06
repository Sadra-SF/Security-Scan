from django.contrib import admin
from .models import Evidence


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "finding",
        "kind",
        "content_type",
        "size",
        "created_at",
    )
    search_fields = ("id", "finding__id", "finding__title", "sha256", "request_id", "response_id")
    list_filter = ("kind", "content_type", "created_at")
    ordering = ("-created_at",)