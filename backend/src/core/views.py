from __future__ import annotations

from datetime import datetime, timezone

from django.db import transaction
from django.utils import timezone as dj_timezone
from django.shortcuts import get_object_or_404

from rest_framework import status, pagination
from rest_framework.permissions import AllowAny  # TODO: switch to IsAuthenticated + RBAC
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Asset, ScanProfile, ScanRun
from .tasks import orchestrate_scan


class ScanRunPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ScansView(APIView):
    authentication_classes = []  # placeholder
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Scans"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "asset_id": {"type": "integer"},
                    "profile_id": {"type": "integer"},
                },
                "required": ["asset_id", "profile_id"],
            }
        },
        responses={201: {"type": "object", "properties": {"scan_run_id": {"type": "integer"}, "status": {"type": "string"}}}},
    )
    def post(self, request):
        data = request.data or {}
        asset_id = data.get("asset_id")
        profile_id = data.get("profile_id")
        if not asset_id or not profile_id:
            return Response({"detail": "asset_id and profile_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        asset = get_object_or_404(Asset, pk=asset_id)
        profile = get_object_or_404(ScanProfile, pk=profile_id)

        with transaction.atomic():
            run = ScanRun.objects.create(
                asset=asset,
                profile=profile,
                status="queued",
                started_at=None,
                ended_at=None,
                meta={},
            )

        # Fire-and-forget orchestration
        orchestrate_scan.delay(run.id)

        return Response({"scan_run_id": run.id, "status": run.status}, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Scans"],
        parameters=[
            OpenApiParameter(name="page", location=OpenApiParameter.QUERY, required=False, type=int),
            OpenApiParameter(name="page_size", location=OpenApiParameter.QUERY, required=False, type=int),
        ],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        qs = ScanRun.objects.select_related("asset", "profile").order_by("-id")
        paginator = ScanRunPagination()
        page = paginator.paginate_queryset(qs, request)
        results = []
        for run in page:
            results.append(
                {
                    "id": run.id,
                    "asset": {"id": run.asset_id, "name": run.asset.name, "type": run.asset.type},
                    "profile": {"id": run.profile_id, "name": run.profile.name},
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "ended_at": run.ended_at.isoformat() if run.ended_at else None,
                    "meta": run.meta,
                }
            )
        return paginator.get_paginated_response(results)