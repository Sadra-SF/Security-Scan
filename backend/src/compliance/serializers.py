from rest_framework import serializers
from .models import (
    ComplianceFramework, ComplianceControl, ComplianceTag,
    ComplianceMapping, ComplianceAssessment
)


class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = ComplianceFramework
        fields = (
            "id",
            "name",
            "type",
            "type_display",
            "version",
            "description",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceControlSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = ComplianceControl
        fields = (
            "id",
            "framework",
            "framework_name",
            "control_id",
            "title",
            "description",
            "type",
            "type_display",
            "severity",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceMappingSerializer(serializers.ModelSerializer):
    control_title = serializers.CharField(source='control.title', read_only=True)
    framework_name = serializers.CharField(source='control.framework.name', read_only=True)
    mapping_type_display = serializers.CharField(source='get_mapping_type_display', read_only=True)

    class Meta:
        model = ComplianceMapping
        fields = (
            "id",
            "control",
            "control_title",
            "framework_name",
            "finding_type",
            "finding_pattern",
            "mapping_type",
            "mapping_type_display",
            "confidence",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceAssessmentSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    assessment_status_display = serializers.CharField(source='get_assessment_status_display', read_only=True)
    compliance_status_display = serializers.CharField(source='get_compliance_status_display', read_only=True)

    class Meta:
        model = ComplianceAssessment
        fields = (
            "id",
            "framework",
            "framework_name",
            "target",
            "target_name",
            "project",
            "project_name",
            "assessment_status",
            "assessment_status_display",
            "compliance_status",
            "compliance_status_display",
            "overall_score",
            "control_scores",
            "findings_count",
            "last_assessed_at",
            "next_assessment_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


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