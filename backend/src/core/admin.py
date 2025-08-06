from django.contrib import admin
from .models import Asset, ScanProfile, ScanRun


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "url_or_cidr", "created_at")
    search_fields = ("name", "url_or_cidr")
    list_filter = ("type",)


@admin.register(ScanProfile)
class ScanProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    readonly_fields = ()


@admin.register(ScanRun)
class ScanRunAdmin(admin.ModelAdmin):
    list_display = ("id", "asset", "profile", "status", "started_at", "ended_at")
    list_filter = ("status", "profile")
    search_fields = ("id", "asset__name", "profile__name")