from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import Finding
from .serializers import FindingSerializer
from .filters import FindingFilter


class FindingViewSet(viewsets.ModelViewSet):
    """
    List/retrieve/partial_update Findings.
    Includes bulk-update action for simple status updates.
    """
    queryset = Finding.objects.select_related(
        "target", "target__project", "scan"
    ).all()
    serializer_class = FindingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]  # disable create/destroy/update
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = FindingFilter
    search_fields = ["title", "description", "locations"]
    ordering_fields = ["last_seen_at", "created_at", "severity", "status"]
    ordering = ["-last_seen_at"]

    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request):
        """
        Body: { "ids": [..], "status": "..." }
        Scope: simple status update only.
        """
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status is required for bulk update"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate status choice
        valid = [c[0] for c in Finding.Status.choices]
        if new_status not in valid:
            return Response({"detail": f"Invalid status. Must be one of: {', '.join(valid)}"}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(id__in=ids)
        updated = qs.update(status=new_status)
        return Response({"updated": updated}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="dashboard-summary")
    def dashboard_summary(self, request):
        """
        Lightweight aggregates for dashboard:
          - open_by_severity: counts for severity where status == open
          - new_last_7d: count of findings with created_at within last 7 days
          - scans_last_7d: count of scans finished/started within last 7 days
          - top_targets: top 5 targets by open findings count
          - compliance_counts: simple framework/tag counts if compliance tags exist
        Optional filters: project_id to scope to a single project.
        """
        project_id = request.query_params.get("project_id")
        seven_days_ago = timezone.now() - timedelta(days=7)

        base = Finding.objects.select_related("target", "target__project").all()
        if project_id:
            base = base.filter(target__project_id=project_id)

        open_qs = base.filter(status=Finding.Status.OPEN)

        # open_by_severity
        sev_counts = (
            open_qs.values("severity")
            .annotate(count=Count("id"))
            .order_by()
        )
        open_by_severity = {row["severity"]: row["count"] for row in sev_counts}

        # new_last_7d
        new_last_7d = base.filter(created_at__gte=seven_days_ago).count()

        # scans_last_7d
        from scans.models import Scan
        scans_qs = Scan.objects.all()
        if project_id:
            scans_qs = scans_qs.filter(target__project_id=project_id)
        scans_last_7d = scans_qs.filter(
            Q(started_at__gte=seven_days_ago) | Q(finished_at__gte=seven_days_ago)
        ).count()

        # top_targets by open count
        top_targets = (
            open_qs.values("target_id", "target__name")
            .annotate(open_count=Count("id"))
            .order_by("-open_count")[:5]
        )
        top_targets_out = [
            {"id": r["target_id"], "name": r["target__name"], "open_count": r["open_count"]}
            for r in top_targets
        ]

        # compliance_counts
        compliance_counts = {}
        try:
            # Try through M2M named 'compliance_tags'
            compl = open_qs.values("compliance_tags__framework").annotate(count=Count("id")).order_by()
            for row in compl:
                key = row["compliance_tags__framework"]
                if key:
                    compliance_counts[key] = compliance_counts.get(key, 0) + row["count"]
        except Exception:
            try:
                # Try reverse generic name
                compl = open_qs.values("compliancetag__framework").annotate(count=Count("id")).order_by()
                for row in compl:
                    key = row["compliancetag__framework"]
                    if key:
                        compliance_counts[key] = compliance_counts.get(key, 0) + row["count"]
            except Exception:
                compliance_counts = {}

        return Response(
            {
                "open_by_severity": open_by_severity,
                "new_last_7d": new_last_7d,
                "scans_last_7d": scans_last_7d,
                "top_targets": top_targets_out,
                "compliance_counts": compliance_counts,
            }
        )