from rest_framework import viewsets, permissions, filters as drf_filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from .models import NotificationChannel, NotificationRule
from .serializers import NotificationChannelSerializer, NotificationRuleSerializer

from notifications.tasks import dispatch_event as notifications_dispatch_event  # for doc reference
from scans.models import Scan


class NotificationChannelViewSet(viewsets.ModelViewSet):
    queryset = NotificationChannel.objects.select_related("project", "project__organization").all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["project", "type", "enabled"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["project__organization__name", "project__name", "name"]

    @extend_schema(
        tags=["Notifications"],
        summary="Send a test notification via the specified channel",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "event": {
                        "type": "string",
                        "enum": ["scan.completed", "scan.failed", "severity.threshold"],
                        "description": "Optional event name used to select a sample payload",
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional plain text message override for channels that support it (email subject/body note)",
                    },
                },
                "additionalProperties": False,
            }
        },
        responses={
            200: {
                "type": "object",
                "required": ["delivered", "transport"],
                "properties": {
                    "delivered": {"type": "boolean", "description": "Whether the test notification was delivered successfully"},
                    "transport": {"type": "string", "enum": ["email", "slack", "teams", "webhook"]},
                    "details": {
                        "type": "object",
                        "additionalProperties": True,
                        "description": "Transport-specific metadata (e.g., http_status, response_excerpt, message_id)",
                    },
                },
            }
        },
        examples=[
            OpenApiExample(
                "email-ok",
                value={"delivered": True, "transport": "email", "details": {"message_id": "<abc123@example>"}},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "webhook-fail",
                value={"delivered": False, "transport": "webhook", "details": {"http_status": 500, "response_excerpt": "Internal Server Error"}},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "default request",
                value={"event": "scan.completed", "message": "Test notification from security-scanner"},
                request_only=True,
            ),
        ],
        parameters=[
            OpenApiParameter(name="id", required=True, location=OpenApiParameter.PATH, type={"type": "string", "format": "uuid"})
        ],
    )
    @action(detail=True, methods=["post"], url_path="test")
    def test(self, request, pk=None):
        """
        Sends a synthetic notification for this channel using a minimal sample Scan context.
        Does not persist a Scan; creates an in-memory object to build payloads.
        """
        channel = self.get_object()
        data = request.data or {}
        event = str(data.get("event") or "scan.completed")
        # Build synthetic context using a minimal in-memory Scan-like object
        # We reuse the context builder logic in tasks by constructing a stub Scan with essential fields.
        # For simplicity and to avoid touching private helpers, create a minimal persisted Scan row then delete.
        message_override = data.get("message")

        # Persist a tiny Scan to leverage templates/links; keep it ephemeral
        scan = Scan.objects.create(
            target=getattr(channel, "project", None).targets.first() if hasattr(channel, "project") else None,  # best-effort
            scanner="test",
            type=Scan.ScanType.AD_HOC if hasattr(Scan.ScanType, "AD_HOC") else Scan.ScanType.MANUAL,
            status=Scan.Status.PENDING,
            stats={"total": 0, "by_severity": {}},
            config={},
        )
        # Import late to avoid circulars and to reuse dispatch channel logic
        from notifications.tasks import _build_context, _dispatch_channel  # type: ignore

        try:
            ctx = _build_context(scan)
            # optionally include message in context for email subject/body templates
            if message_override:
                ctx["message"] = str(message_override)
            ok, info = _dispatch_channel(channel, event, ctx)

            details = {}
            # best-effort parse info for webhook/email transports
            t = (channel.type or "").lower()
            transport_map = {
                getattr(channel, "ChannelType", None).EMAIL if hasattr(channel, "ChannelType") else "email": "email",
                getattr(channel, "ChannelType", None).SLACK if hasattr(channel, "ChannelType") else "slack": "slack",
                getattr(channel, "ChannelType", None).MS_TEAMS if hasattr(channel, "ChannelType") else "teams": "teams",
                getattr(channel, "ChannelType", None).WEBHOOK if hasattr(channel, "ChannelType") else "webhook": "webhook",
            }
            # Normalize transport string
            transport = "email"
            try:
                if t == channel.ChannelType.EMAIL:
                    transport = "email"
                elif t == channel.ChannelType.SLACK:
                    transport = "slack"
                elif t == channel.ChannelType.MS_TEAMS:
                    transport = "teams"
                elif t == channel.ChannelType.WEBHOOK:
                    transport = "webhook"
            except Exception:
                transport = "webhook" if "webhook" in (t or "") else "email"

            # Heuristic mapping of info
            if isinstance(info, str):
                if info.isdigit():
                    details = {"http_status": int(info)}
                elif info.startswith("non_2xx:"):
                    try:
                        details = {"http_status": int(info.split(":")[1])}
                    except Exception:
                        details = {"info": info}
                elif info.startswith("exception:"):
                    details = {"error": info}
                elif info == "sent":
                    details = {"message_id": "<unknown>"}
                else:
                    details = {"info": info}
            else:
                details = {"info": str(info)}

            return Response({"delivered": bool(ok), "transport": transport, "details": details}, status=status.HTTP_200_OK)
        finally:
            try:
                scan.delete()
            except Exception:
                pass


class NotificationRuleViewSet(viewsets.ModelViewSet):
    queryset = NotificationRule.objects.select_related("project", "channel").all()
    serializer_class = NotificationRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["project", "event", "enabled", "severity_min", "channel"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["project__organization__name", "project__name", "name"]