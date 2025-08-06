from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "format",
        "status",
        "version",
        "template",
        "generated_at",
        "created_at",
        "id",
    )
    search_fields = ("title", "id", "project__name", "project__organization__name")
    list_filter = ("status", "format", "created_at", "generated_at", "project__organization")
    ordering = ("-generated_at", "-created_at")