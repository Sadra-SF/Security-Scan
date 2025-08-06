from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import Schedule
from .serializers import ScheduleSerializer
from scans.tasks import start_scan
from django.utils import timezone
from .tasks import compute_next_run


class ScheduleViewSet(viewsets.ModelViewSet):
    """
    CRUD for schedules (skeleton, no Celery beat integration yet).
    Adds POST /schedules/{id}/run-now to enqueue a scan for the linked target.
    """
    queryset = Schedule.objects.select_related("target", "target__project").all()
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["target", "enabled", "scanner"]
    search_fields = ["scanner"]
    ordering_fields = ["created_at", "updated_at", "last_run_at", "next_run_at"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"], url_path="run-now")
    def run_now(self, request, pk=None):
        schedule = self.get_object()
        target = schedule.target
        # Create a Scan row minimally via serializer/ORM is out-of-scope; the Celery control task
        # will handle planning. We just enqueue start_scan for a synthesized or minimal persisted Scan.
        # For simplicity, create a Scan and queue it (status pending).
        from scans.models import Scan

        scan = Scan.objects.create(
            target=target,
            scanner=schedule.scanner or "auto",
            type=Scan.ScanType.SCHEDULED,
            status=Scan.Status.PENDING,
            config=schedule.config or {},
        )
        start_scan.delay(str(scan.id))
        return Response({"scan_id": str(scan.id), "status": "queued"}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        tags=["Schedules"],
        summary="Preview upcoming run times for a cron and timezone",
        description="Optional helper for UI to display the next N run times without saving a schedule",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "cron": {"type": "string", "example": "0 2 * * *"},
                    "timezone": {"type": "string", "example": "UTC"},
                    "count": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "required": ["cron", "timezone"],
                "additionalProperties": False,
            }
        },
        responses={
            200: {
                "type": "object",
                "required": ["next_runs"],
                "properties": {"next_runs": {"type": "array", "items": {"type": "string", "format": "date-time"}}},
            }
        },
        examples=[
            OpenApiExample(
                "sample request",
                value={"cron": "0 2 * * *", "timezone": "UTC", "count": 5},
                request_only=True,
            ),
            OpenApiExample(
                "sample response",
                value={
                    "next_runs": [
                        "2025-08-07T02:00:00Z",
                        "2025-08-08T02:00:00Z",
                        "2025-08-09T02:00:00Z",
                        "2025-08-10T02:00:00Z",
                        "2025-08-11T02:00:00Z",
                    ]
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="preview-next-run")
    def preview_next_run(self, request):
        data = request.data or {}
        cron = (data.get("cron") or "").strip()
        tz_name = (data.get("timezone") or "").strip()
        count = int(data.get("count") or 5)
        if count < 1:
            count = 1
        if count > 20:
            count = 20

        # Build a transient Schedule instance to pass through compute_next_run
        from types import SimpleNamespace
        mock = SimpleNamespace(
            minute="*",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            config={},
        )
        # Parse cron into fields if possible (minute hour dom mon dow)
        try:
            parts = cron.split()
            if len(parts) == 5:
                mock.minute, mock.hour, mock.day_of_month, mock.month_of_year, mock.day_of_week = parts
        except Exception:
            pass

        # Start from now in the requested timezone if provided
        now = timezone.now()
        if tz_name:
            try:
                import pytz
                now = now.astimezone(pytz.timezone(tz_name))
            except Exception:
                pass

        runs = []
        cur = now
        for _ in range(count):
            nxt = compute_next_run(mock, cur)
            if not nxt:
                break
            # Normalize to UTC ISO-8601 Z
            try:
                if nxt.tzinfo is None:
                    nxt = timezone.make_aware(nxt, timezone=timezone.utc)
                runs.append(nxt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
            except Exception:
                runs.append(nxt.isoformat())
            cur = nxt

        return Response({"next_runs": runs}, status=status.HTTP_200_OK)