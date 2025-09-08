from rest_framework import viewsets, permissions, filters as drf_filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import (
    ComplianceFramework, ComplianceControl, ComplianceTag,
    ComplianceMapping, ComplianceAssessment
)
from .serializers import (
    ComplianceFrameworkSerializer, ComplianceControlSerializer,
    ComplianceTagSerializer, ComplianceMappingSerializer,
    ComplianceAssessmentSerializer
)
from .assessment import ComplianceAssessmentService


class ComplianceFrameworkViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Compliance Frameworks.
    """
    queryset = ComplianceFramework.objects.all()
    serializer_class = ComplianceFrameworkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["type", "is_active"]
    search_fields = ["name", "type", "description"]
    ordering_fields = ["type", "name", "created_at"]
    ordering = ["type", "name"]

    @action(detail=True, methods=['post'])
    def assess_target(self, request, pk=None):
        """
        Assess compliance for a target against this framework.
        """
        framework = self.get_object()
        target_id = request.data.get('target_id')
        project_id = request.data.get('project_id')

        if not target_id:
            return Response(
                {'error': 'target_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from targets.models import Target
        from projects.models import Project

        try:
            target = Target.objects.get(id=target_id)
            project = None
            if project_id:
                project = Project.objects.get(id=project_id)

            assessment = ComplianceAssessmentService.assess_target_compliance(
                target, framework, project
            )

            serializer = ComplianceAssessmentSerializer(assessment)
            return Response(serializer.data)

        except Target.DoesNotExist:
            return Response(
                {'error': 'Target not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def controls(self, request, pk=None):
        """
        Get all controls for this framework.
        """
        framework = self.get_object()
        controls = ComplianceControl.objects.filter(framework=framework)
        serializer = ComplianceControlSerializer(controls, many=True)
        return Response(serializer.data)


class ComplianceControlViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Compliance Controls.
    """
    queryset = ComplianceControl.objects.all()
    serializer_class = ComplianceControlSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["framework", "type", "severity", "is_active"]
    search_fields = ["control_id", "title", "description"]
    ordering_fields = ["framework", "control_id", "severity", "created_at"]
    ordering = ["framework", "control_id"]


class ComplianceAssessmentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Compliance Assessments.
    """
    queryset = ComplianceAssessment.objects.all()
    serializer_class = ComplianceAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["framework", "target", "project", "assessment_status", "compliance_status"]
    search_fields = ["framework__name", "target__name"]
    ordering_fields = ["-last_assessed_at", "framework", "target", "compliance_status"]
    ordering = ["-last_assessed_at"]

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """
        Get detailed compliance report for this assessment.
        """
        assessment = self.get_object()
        report = ComplianceAssessmentService.get_compliance_report(
            assessment.target, assessment.framework
        )
        return Response(report)

    @action(detail=False, methods=['post'])
    def bulk_assess(self, request):
        """
        Bulk assess compliance for multiple targets.
        """
        framework_id = request.data.get('framework_id')
        target_ids = request.data.get('target_ids', [])
        project_id = request.data.get('project_id')

        if not framework_id:
            return Response(
                {'error': 'framework_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not target_ids:
            return Response(
                {'error': 'target_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            framework = ComplianceFramework.objects.get(id=framework_id)
            from targets.models import Target
            from projects.models import Project

            targets = Target.objects.filter(id__in=target_ids)
            project = None
            if project_id:
                project = Project.objects.get(id=project_id)

            stats = ComplianceAssessmentService.bulk_assess_compliance(
                list(targets), framework, project
            )

            return Response(stats)

        except ComplianceFramework.DoesNotExist:
            return Response(
                {'error': 'Framework not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ComplianceMappingViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Compliance Mappings.
    """
    queryset = ComplianceMapping.objects.all()
    serializer_class = ComplianceMappingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["control", "finding_type", "mapping_type", "is_active"]
    search_fields = ["finding_type", "finding_pattern"]
    ordering_fields = ["control", "finding_type", "confidence", "created_at"]
    ordering = ["control", "finding_type"]


class ComplianceTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of Compliance Tags (legacy support).
    """
    queryset = ComplianceTag.objects.all()
    serializer_class = ComplianceTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["category", "slug"]
    search_fields = ["slug", "title", "description", "category"]
    ordering_fields = ["category", "slug", "title", "created_at"]
    ordering = ["category", "slug"]