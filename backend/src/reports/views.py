import mimetypes
import os

from django.http import FileResponse, Http404, HttpResponseRedirect
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer
from .tasks import generate_report, generate_report_sync


class ReportViewSet(viewsets.ModelViewSet):
    """
    Basic CRUD for reports with create triggering async generation.
    Download action serves/redirects to generated artifact.
    """
    queryset = Report.objects.select_related("project").all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ReportSerializer

    def get_serializer_class(self):
        if self.action in ("create",):
            return ReportCreateSerializer
        return ReportSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = Report.objects.create(
            project=serializer.validated_data["project"],
            title=serializer.validated_data.get("title") or f"Report ({serializer.validated_data['format']})",
            version=serializer.validated_data.get("version") or "",
            template=serializer.validated_data.get("template") or "",
            format=serializer.validated_data["format"],
            status=Report.Status.GENERATING,  # queueing immediately
            filters=serializer.validated_data.get("filters") or {},
        )
        # Try async enqueue, fallback to sync if Celery fails
        try:
            generate_report.delay(str(report.id))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Async report generation failed for report {report.id}, falling back to synchronous: {e}")
            try:
                generate_report_sync(str(report.id))
            except Exception as sync_e:
                logger.error(f"Synchronous report generation also failed for report {report.id}: {sync_e}")
                # Update status to failed
                report.status = Report.Status.FAILED
                report.save(update_fields=["status", "updated_at"])

        out = ReportSerializer(report)
        headers = {"Location": self.request.build_absolute_uri(f"/api/v1/reports/{report.id}/")}
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        try:
            report = self.get_queryset().get(pk=pk)
        except Report.DoesNotExist:
            raise Http404

        if report.status != Report.Status.READY or not report.storage_url:
            return Response({"detail": "Report not ready"}, status=status.HTTP_409_CONFLICT)

        # If storage_url is an HTTP(S) URL, redirect.
        if str(report.storage_url).startswith(("http://", "https://")):
            return HttpResponseRedirect(report.storage_url)

        # Otherwise, assume local filesystem path.
        abs_path = report.storage_url
        if not os.path.exists(abs_path):
            raise Http404("File not found")
        filename = os.path.basename(abs_path)
        mime, _ = mimetypes.guess_type(filename)
        mime = mime or "application/octet-stream"
        response = FileResponse(open(abs_path, "rb"), content_type=mime)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response