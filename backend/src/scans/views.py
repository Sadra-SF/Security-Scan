import logging
from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Scan
from .serializers import ScanSerializer, TriggerScanSerializer
from .filters import ScanFilter
from scans.tasks import start_scan

logger = logging.getLogger(__name__)


class ScanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Scan with filtering/search/ordering.
    Provides POST /api/v1/scans/trigger to create a queued Scan and enqueue Celery task.
    """
    queryset = Scan.objects.select_related("target", "target__project", "target__project__organization").all()
    serializer_class = ScanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ScanFilter
    search_fields = ["scanner"]
    ordering_fields = ["started_at", "created_at"]
    ordering = ["-started_at", "-created_at"]

    @action(detail=False, methods=["post"], url_path="trigger")
    def trigger(self, request):
        """
        Body: { "target_id": UUID, "mode|type": "...", "scanner_keys": ["zap", "nmap"]? }
        Creates Scan row in 'pending' and enqueues scans.tasks.start_scan.delay(scan.id).
        """
        logger.info(f"Scan trigger request received: {request.data}")

        serializer = TriggerScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data["target"]
        scan_type = serializer.validated_data["type"]
        scanner_keys = serializer.validated_data.get("scanner_keys") or []

        logger.info(f"Creating scan for target {target.id} ({target.name}) with type {scan_type} and scanner_keys {scanner_keys}")

        scan = Scan.objects.create(
            target=target,
            scanner=",".join(scanner_keys) if scanner_keys else "auto",
            type=scan_type,
            status=Scan.Status.PENDING,
            config={},
        )

        logger.info(f"Scan created with ID {scan.id}, attempting to enqueue Celery task")

        try:
            # enqueue celery task
            start_scan.delay(str(scan.id))
            logger.info(f"Successfully enqueued scan task for scan {scan.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue scan task for scan {scan.id}: {e}")
            # For testing: run scan synchronously if Celery fails
            logger.info(f"Running scan {scan.id} synchronously as fallback")
            try:
                from scans.tasks import start_scan
                start_scan(str(scan.id))
                logger.info(f"Successfully completed synchronous scan for scan {scan.id}")
            except Exception as sync_e:
                logger.error(f"Failed to run synchronous scan for scan {scan.id}: {sync_e}")
                scan.status = Scan.Status.FAILED
                scan.save()

        return Response(ScanSerializer(scan).data, status=status.HTTP_201_CREATED)