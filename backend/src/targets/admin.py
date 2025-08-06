from django.contrib import admin
from .models import Target


@admin.register(Target)
class TargetAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "project", "type", "created_at", "updated_at", "id")
    search_fields = ("name", "slug", "id", "project__name", "project__organization__name")
    list_filter = ("type", "created_at", "project__organization")
    ordering = ("project__organization__name", "project__name", "name")