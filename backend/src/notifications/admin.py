from django.contrib import admin
from .models import NotificationChannel, NotificationRule


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "type",
        "enabled",
        "created_at",
        "id",
    )
    search_fields = ("name", "id", "project__name", "project__organization__name")
    list_filter = ("type", "enabled", "created_at", "project__organization")
    ordering = ("project__organization__name", "project__name", "name")


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "event",
        "severity_min",
        "channel",
        "enabled",
        "created_at",
        "id",
    )
    search_fields = ("name", "id", "project__name", "project__organization__name", "channel__name")
    list_filter = ("event", "severity_min", "enabled", "created_at", "project__organization")
    ordering = ("project__organization__name", "project__name", "name")