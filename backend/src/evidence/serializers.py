from rest_framework import serializers
from .models import Evidence


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = (
            "id",
            "finding",
            "kind",
            "storage_url",
            "content_type",
            "size",
            "sha256",
            "request_id",
            "response_id",
            "metadata",
            "created_at",
            "updated_at",
        )