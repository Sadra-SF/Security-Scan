from rest_framework import serializers
from .models import Organization, Project


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name", "slug", "metadata", "created_at", "updated_at")


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "visibility",
            "settings",
            "created_at",
            "updated_at",
        )