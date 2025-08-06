from django.contrib import admin
from .models import IntegrationToken, Webhook


@admin.register(IntegrationToken)
class IntegrationTokenAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "token_hash",
        "expires_at",
        "created_at",
        "id",
    )
    search_fields = ("name", "id", "project__name", "project__organization__name", "token_hash")
    list_filter = ("created_at", "expires_at", "project__organization")
    ordering = ("project__organization__name", "project__name", "name")


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "url",
        "enabled",
        "created_at",
        "id",
    )
    search_fields = ("name", "id", "project__name", "project__organization__name", "url")
    list_filter = ("enabled", "created_at", "project__organization")
    ordering = ("project__organization__name", "project__name", "name")