from rest_framework import serializers
from .models import Scan
from targets.models import Target


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = (
            "id",
            "target",
            "scanner",
            "type",
            "status",
            "config",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
            "stats",
        )


class TriggerScanSerializer(serializers.Serializer):
    target_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=Scan.ScanType.choices, required=False)
    type = serializers.ChoiceField(choices=Scan.ScanType.choices, required=False)
    scanner_keys = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, allow_empty=True
    )

    def validate(self, attrs):
        # Validate target exists
        try:
            target = Target.objects.get(pk=attrs["target_id"])
        except Target.DoesNotExist:
            raise serializers.ValidationError({"target_id": "Target not found"})

        # Normalize: support either 'mode' or 'type' input; map to 'type'
        scan_type = attrs.get("type") or attrs.get("mode") or Scan.ScanType.MANUAL
        # Ensure value is a valid choice
        valid_values = [c[0] for c in Scan.ScanType.choices]
        if scan_type not in valid_values:
            raise serializers.ValidationError({"type": f"Invalid type. Must be one of: {', '.join(valid_values)}"})

        attrs["target"] = target
        attrs["type"] = scan_type
        return attrs