from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

import json
import hmac
import time
from hashlib import sha256
import requests

from .models import IntegrationToken, Webhook
from .serializers import IntegrationTokenSerializer, WebhookSerializer


class IntegrationTokenViewSet(viewsets.ModelViewSet):
    """
    list/create/destroy Integration Tokens.
    On create, returns raw_token once; only hash is stored.
    """
    queryset = IntegrationToken.objects.select_related("project", "project__organization").all()
    serializer_class = IntegrationTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["project", "expires_at"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "updated_at", "name", "expires_at"]
    ordering = ["project__organization__name", "project__name", "name"]


class WebhookViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD for Webhooks.
    """
    queryset = Webhook.objects.select_related("project", "project__organization").all()
    serializer_class = WebhookSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["project", "enabled"]
    search_fields = ["name", "url"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["project__organization__name", "project__name", "name"]

    @extend_schema(
        tags=["Integrations"],
        summary="Send a test webhook to the configured URL",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "sample_event": {"type": "string", "enum": ["scan.completed", "scan.failed", "severity.threshold"]},
                    "payload_overrides": {"type": "object", "additionalProperties": True, "description": "Optional JSON overrides merged into the sample payload before sending"},
                },
                "additionalProperties": False,
            }
        },
        responses={
            200: {
                "type": "object",
                "required": ["delivered", "status_code", "duration_ms"],
                "properties": {
                    "delivered": {"type": "boolean"},
                    "status_code": {"type": "integer"},
                    "duration_ms": {"type": "integer"},
                    "response_excerpt": {"type": "string", "description": "First N characters of response body for diagnostics"},
                    "headers": {"type": "object", "additionalProperties": True},
                },
            }
        },
        examples=[
            OpenApiExample(
                "severity-threshold",
                value={"sample_event": "severity.threshold", "payload_overrides": {"threshold": "high"}},
                request_only=True,
            ),
            OpenApiExample(
                "delivered",
                value={"delivered": True, "status_code": 200, "duration_ms": 112, "response_excerpt": "OK"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
        parameters=[
            OpenApiParameter(name="id", required=True, location=OpenApiParameter.PATH, type={"type": "string", "format": "uuid"})
        ],
    )
    @action(detail=True, methods=["post"], url_path="test")
    def test(self, request, pk=None):
        webhook = self.get_object()
        data = request.data or {}
        sample_event = str(data.get("sample_event") or "scan.completed")
        overrides = data.get("payload_overrides") or {}

        # Build sample payload consistent with notifications.webhook structure
        payload = {
            "event": sample_event,
            "project": {
                "id": str(getattr(webhook.project, "id", "")),
                "name": getattr(webhook.project, "name", ""),
                "organization_id": str(getattr(getattr(webhook.project, "organization", None), "id", "")),
                "organization_name": getattr(getattr(webhook.project, "organization", None), "name", ""),
            },
            "target": None,
            "scan_id": None,
            "summary": {"total": 0, "by_severity": {}},
            "links": {},
        }
        try:
            payload.update(overrides)
        except Exception:
            pass

        body_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        headers = {"Content-Type": "application/json"}

        # Reuse signing approach like notifications._dispatch_webhook
        secret_hex = None
        # Webhook model stores secret hash; for test purposes we assume serializer/model provides a transient secret in headers metadata if configured.
        # If not available, send unsigned.
        try:
            # If the instance has a 'secret' transient attr or headers include 'X-Use-Secret': True just for internal test, ignore silently if absent.
            secret_value = None
            if hasattr(webhook, "secret"):  # unlikely
                secret_value = getattr(webhook, "secret")
            else:
                # attempt: if headers has {"use_project_secret": "raw"} not secure; fallback to None
                secret_value = None
            if secret_value:
                sig = hmac.new(str(secret_value).encode("utf-8"), body_json.encode("utf-8"), sha256).hexdigest()
                headers["X-Signature"] = sig
        except Exception:
            pass

        # Merge user-provided headers from model
        try:
            model_headers = webhook.headers or {}
            if isinstance(model_headers, dict):
                for k, v in model_headers.items():
                    headers[str(k)] = str(v)
        except Exception:
            pass

        start = time.perf_counter()
        delivered = False
        status_code = 0
        response_excerpt = ""
        resp_headers = {}

        try:
            timeout = 5
            resp = requests.post(webhook.url, data=body_json, headers=headers, timeout=timeout)
            status_code = int(resp.status_code)
            delivered = 200 <= status_code < 300
            # cap to 512 chars
            text = ""
            try:
                text = resp.text or ""
            except Exception:
                text = ""
            response_excerpt = (text[:512]) if text else ""
            # capture some headers safely
            try:
                resp_headers = dict(resp.headers) if hasattr(resp, "headers") else {}
            except Exception:
                resp_headers = {}
        except Exception as e:
            delivered = False
            status_code = 0
            response_excerpt = f"exception:{type(e).__name__}:{e}"
            resp_headers = {}

        duration_ms = int((time.perf_counter() - start) * 1000)

        return Response(
            {
                "delivered": delivered,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "response_excerpt": response_excerpt,
                "headers": resp_headers,
            },
            status=status.HTTP_200_OK,
        )