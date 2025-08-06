from datetime import datetime, timezone
import os

from rest_framework.response import Response
from rest_framework.views import APIView

import redis
from django.conf import settings


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # Try to ping Redis broker quickly; do not crash on failure.
        broker_status = "unknown"
        try:
            url = getattr(settings, "CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
            r = redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
            if r.ping():
                broker_status = "ok"
            else:
                broker_status = "unreachable"
        except Exception:
            broker_status = "unavailable"

        return Response(
            {
                "status": "ok",
                "time": datetime.now(timezone.utc).isoformat(),
                "celery_broker": broker_status,
            }
        )


class CeleryHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # This is a lightweight acknowledgement that the app is configured for Celery.
        # It does not guarantee worker availability but confirms endpoint wiring.
        return Response({"celery": {"acknowledged": True}})