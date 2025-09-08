from rest_framework import serializers
from .models import Evidence


class EvidenceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    correlated_evidence_count = serializers.SerializerMethodField()
    evidence_chain_length = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = (
            "id",
            "finding",
            "kind",
            "file",
            "file_url",
            "storage_url",
            "content_type",
            "size",
            "sha256",
            "request_id",
            "response_id",
            "metadata",
            "correlation_id",
            "correlation_type",
            "parent_evidence",
            "tags",
            "correlated_evidence_count",
            "evidence_chain_length",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("file_url", "size", "sha256", "correlated_evidence_count", "evidence_chain_length")

    def get_file_url(self, obj):
        return obj.file_url

    def get_correlated_evidence_count(self, obj):
        return obj.correlated_evidence.count()

    def get_evidence_chain_length(self, obj):
        return len(obj.evidence_chain)


class EvidenceUploadSerializer(serializers.Serializer):
    """
    Serializer for evidence file uploads.
    """
    file = serializers.FileField(required=True)
    finding_id = serializers.UUIDField(required=False, allow_null=True)
    kind = serializers.ChoiceField(
        choices=Evidence.Kind.choices,
        default=Evidence.Kind.OTHER
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_file(self, value):
        """
        Validate uploaded file.
        """
        # Check file size (limit to 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

        # Check file type if needed
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',  # Images
            'text/plain', 'text/html', 'text/xml', 'application/json',  # Text
            'application/pdf', 'application/xml',  # Documents
            'application/octet-stream',  # Binary
        ]

        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            # Allow unknown types but log warning
            pass

        return value