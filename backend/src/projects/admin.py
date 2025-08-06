from django.contrib import admin
from .models import Organization, Project


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "updated_at", "id")
    search_fields = ("name", "slug", "id")
    list_filter = ("created_at",)
    ordering = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "visibility", "created_at", "updated_at", "id")
    search_fields = ("name", "slug", "id", "organization__name", "organization__slug")
    list_filter = ("visibility", "created_at", "organization")
    ordering = ("organization__name", "name")