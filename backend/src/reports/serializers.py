from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField(help_text="Convenience URL to GET for downloading the artifact when ready")

    class Meta:
        model = Report
        fields = (
            "id",
            "project",
            "title",
            "version",
            "template",
            "format",
            "status",
            "storage_url",
            "generated_at",
            "filters",
            "created_at",
            "updated_at",
            "meta",
            "download_url",
        )
        read_only_fields = ("status", "storage_url", "generated_at", "created_at", "updated_at", "meta", "download_url")

    def get_download_url(self, obj: Report):
        try:
            if obj.status == Report.Status.READY:
                return f"/api/v1/reports/{obj.id}/download"
        except Exception:
            pass
        return None


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Validates creation payload for a report generation request.
    Accepts filters to narrow dataset; ensures format/type is one of allowed: ['pdf', 'csv'].
    """
    type = serializers.CharField(write_only=True, required=False, help_text="Alias for format; one of: pdf,csv")

    class Meta:
        model = Report
        fields = (
            "id",
            "project",
            "title",
            "version",
            "template",
            "format",
            "type",
            "filters",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        # Normalize type/format with 'format' taking precedence over 'type'
        type_alias = attrs.pop("type", None)
        fmt = attrs.get("format") or type_alias
        if not fmt:
            fmt = "pdf"
        fmt = str(fmt).lower()
        if fmt not in ("pdf", "csv"):
            raise serializers.ValidationError({"format": "Invalid format. Must be one of: ['pdf','csv']"})
        attrs["format"] = fmt
        # Default title if missing
        if not attrs.get("title"):
            attrs["title"] = f"Report ({fmt.upper()})"
        # Ensure filters is a dict
        filters = attrs.get("filters") or {}
        if not isinstance(filters, dict):
            raise serializers.ValidationError({"filters": "filters must be an object/dict"})
        attrs["filters"] = filters
        return attrs