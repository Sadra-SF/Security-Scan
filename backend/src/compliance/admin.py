from django.contrib import admin
from .models import ComplianceTag


@admin.register(ComplianceTag)
class ComplianceTagAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "category", "created_at", "updated_at")
    search_fields = ("slug", "title", "category")
    list_filter = ("category", "created_at")
    ordering = ("category", "slug")