from rest_framework import serializers
from .models import Finding


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = (
            "id",
            "target",
            "scan",
            "title",
            "description",
            "severity",
            "status",
            "cvss_score",
            "dedupe_hash",
            "locations",
            "evidence_refs",
            "metadata",
            "first_seen_at",
            "last_seen_at",
            "created_at",
            "updated_at",
        )