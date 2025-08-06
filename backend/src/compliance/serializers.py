from rest_framework import serializers
from .models import ComplianceTag


class ComplianceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceTag
        fields = (
            "slug",
            "title",
            "description",
            "category",
            "metadata",
            "created_at",
            "updated_at",
        )