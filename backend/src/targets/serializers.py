from rest_framework import serializers
from .models import Target


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = (
            "id",
            "project",
            "name",
            "slug",
            "type",
            "address",
            "tags",
            "settings",
            "created_at",
            "updated_at",
        )