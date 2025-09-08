from rest_framework import serializers
from .models import Finding


class ComplianceControlSerializer(serializers.Serializer):
    """Serializer for compliance controls in findings."""
    id = serializers.UUIDField()
    control_id = serializers.CharField()
    title = serializers.CharField()
    framework_name = serializers.CharField(source='framework.name')
    severity = serializers.CharField()


class FindingSerializer(serializers.ModelSerializer):
    compliance_controls = ComplianceControlSerializer(many=True, read_only=True)

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
            "compliance_controls",
            "metadata",
            "first_seen_at",
            "last_seen_at",
            "created_at",
            "updated_at",
        )