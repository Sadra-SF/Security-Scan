from rest_framework import viewsets, permissions, status, filters as drf_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404, HttpResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone
import os
import logging

from .models import Evidence
from .serializers import EvidenceSerializer, EvidenceUploadSerializer
from .recorder import record_evidence_from_content

logger = logging.getLogger(__name__)


class EvidencePermissions(permissions.BasePermission):
    """
    Custom permission class for evidence access.
    Users can only access evidence related to targets/projects they have access to.
    """

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access specific evidence object."""
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if evidence is linked to a finding
        if obj.finding:
            # User should have access to the finding's target/project
            # This is a simplified check - in production you'd check user's project membership
            return True  # For now, allow authenticated users

        # For standalone evidence, check if user created it or has project access
        # This would need to be implemented based on your user/project model
        return True  # For now, allow authenticated users

    def has_permission(self, request, view):
        """Check if user has general permission for evidence operations."""
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        # For list/create operations, we'll filter the queryset
        return True


class EvidenceViewSet(viewsets.ModelViewSet):
    """
    Evidence management endpoints with upload, download, and CRUD operations.
    """
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.IsAuthenticated, EvidencePermissions]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_fields = ["finding", "kind"]
    search_fields = ["content_type", "storage_url", "metadata", "kind"]
    ordering_fields = ["created_at", "size", "kind"]
    ordering = ["-created_at"]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'upload':
            return EvidenceUploadSerializer
        return EvidenceSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = Evidence.objects.select_related("finding").all()

        # If user is not staff/superuser, filter to only evidence they should access
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            # Filter evidence to only those linked to findings from accessible targets/projects
            # This is a simplified implementation - in production you'd check user's project membership
            # For now, we'll allow access to all evidence for authenticated users
            # You could implement more granular permissions here
            pass

        return queryset

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload evidence file and create evidence record.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get the uploaded file
                uploaded_file = request.FILES.get('file')
                if not uploaded_file:
                    return Response(
                        {"error": "No file provided"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Handle large files efficiently
                # For very large files, we might want to stream to temporary storage first
                # For now, read into memory but add size validation
                max_upload_size = 100 * 1024 * 1024  # 100MB limit
                if uploaded_file.size > max_upload_size:
                    return Response(
                        {"error": f"File too large. Maximum size is {max_upload_size // (1024*1024)}MB"},
                        status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                    )

                # Read file content
                file_content = uploaded_file.read()

                # Get metadata from request
                finding_id = serializer.validated_data.get('finding_id')
                kind = serializer.validated_data.get('kind', 'artifact')
                content_type = uploaded_file.content_type or 'application/octet-stream'

                # Find the finding if provided
                finding = None
                if finding_id:
                    from findings.models import Finding
                    try:
                        finding = Finding.objects.get(id=finding_id)
                    except Finding.DoesNotExist:
                        return Response(
                            {"error": "Finding not found"},
                            status=status.HTTP_404_NOT_FOUND
                        )

                # Record the evidence
                evidence = record_evidence_from_content(
                    finding=finding,
                    content=file_content,
                    filename=uploaded_file.name,
                    kind=kind,
                    content_type=content_type,
                    metadata=serializer.validated_data.get('metadata', {})
                )

                # Return the created evidence
                response_serializer = EvidenceSerializer(evidence)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.exception("Evidence upload failed: %s", e)
                return Response(
                    {"error": "Upload failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download evidence file with support for large files and range requests.
        """
        try:
            evidence = self.get_object()

            # Check if file exists
            if not evidence.file:
                return Response(
                    {"error": "No file available for download"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if file exists in storage
            if not default_storage.exists(evidence.file.name):
                return Response(
                    {"error": "File not found in storage"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get file size
            file_size = default_storage.size(evidence.file.name)

            # Handle range requests for resumable downloads
            range_header = request.META.get('HTTP_RANGE')
            if range_header:
                # Parse range header (e.g., "bytes=0-1023")
                try:
                    range_match = range_header.strip().replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if range_match[1] else file_size - 1

                    if start >= file_size or end >= file_size or start > end:
                        return Response(
                            {"error": "Invalid range"},
                            status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
                        )

                    # Create partial response
                    file_handle = default_storage.open(evidence.file.name, 'rb')
                    file_handle.seek(start)
                    content = file_handle.read(end - start + 1)

                    response = HttpResponse(
                        content,
                        status=status.HTTP_206_PARTIAL_CONTENT,
                        content_type=evidence.content_type or 'application/octet-stream'
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Content-Length'] = len(content)
                    response['Accept-Ranges'] = 'bytes'

                except (ValueError, IndexError):
                    return Response(
                        {"error": "Invalid range header"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Regular download - use streaming for large files
                file_handle = default_storage.open(evidence.file.name, 'rb')

                # For large files, use StreamingHttpResponse
                if file_size > 10 * 1024 * 1024:  # 10MB threshold
                    from django.http import StreamingHttpResponse

                    def file_iterator(file_handle, chunk_size=8192):
                        try:
                            while True:
                                chunk = file_handle.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                        finally:
                            file_handle.close()

                    response = StreamingHttpResponse(
                        file_iterator(file_handle),
                        content_type=evidence.content_type or 'application/octet-stream'
                    )
                else:
                    # For smaller files, load into memory
                    response = HttpResponse(
                        file_handle.read(),
                        content_type=evidence.content_type or 'application/octet-stream'
                    )
                    file_handle.close()

                response['Content-Length'] = file_size

            # Set filename for download
            filename = os.path.basename(evidence.file.name)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Accept-Ranges'] = 'bytes'

            # Add cache headers for better performance
            response['Cache-Control'] = 'private, max-age=3600'  # Cache for 1 hour

            return response

        except Http404:
            return Response(
                {"error": "Evidence not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Evidence download failed: %s", e)
            return Response(
                {"error": "Download failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, pk=None):
        """
        Delete evidence file from storage.
        """
        try:
            evidence = self.get_object()

            if evidence.file:
                evidence.delete_file()
                evidence.file = None
                evidence.save(update_fields=['file', 'updated_at'])

            return Response({"message": "File deleted successfully"})

        except Http404:
            return Response(
                {"error": "Evidence not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("File deletion failed: %s", e)
            return Response(
                {"error": "Deletion failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get evidence statistics.
        """
        try:
            queryset = self.get_queryset()
            total_count = queryset.count()
            total_size = queryset.aggregate(
                total_size=Sum('size')
            )['total_size'] or 0

            by_kind = {}
            for evidence in queryset:
                kind = evidence.kind
                by_kind[kind] = by_kind.get(kind, 0) + 1

            return Response({
                "total_count": total_count,
                "total_size": total_size,
                "by_kind": by_kind
            })

        except Exception as e:
            logger.exception("Stats retrieval failed: %s", e)
            return Response(
                {"error": "Stats retrieval failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export evidence in various formats (JSON, CSV, ZIP).
        """
        try:
            queryset = self.get_queryset()
            export_format = request.query_params.get('format', 'json')
            include_files = request.query_params.get('include_files', 'false').lower() == 'true'

            if export_format not in ['json', 'csv', 'zip']:
                return Response(
                    {"error": "Invalid format. Supported: json, csv, zip"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if export_format == 'json':
                return self._export_json(queryset)
            elif export_format == 'csv':
                return self._export_csv(queryset)
            elif export_format == 'zip':
                return self._export_zip(queryset, include_files)

        except Exception as e:
            logger.exception("Evidence export failed: %s", e)
            return Response(
                {"error": "Export failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _export_json(self, queryset):
        """Export evidence as JSON."""
        serializer = EvidenceSerializer(queryset, many=True)
        data = {
            'export_timestamp': timezone.now().isoformat(),
            'total_count': queryset.count(),
            'evidence': serializer.data
        }

        response = Response(data, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="evidence_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        return response

    def _export_csv(self, queryset):
        """Export evidence as CSV."""
        import csv
        from io import StringIO

        buffer = StringIO()
        writer = csv.writer(buffer)

        # Write header
        writer.writerow([
            'ID', 'Kind', 'Content Type', 'Size', 'Created At',
            'Correlation ID', 'Tags', 'File URL', 'Storage URL'
        ])

        # Write data
        for evidence in queryset:
            writer.writerow([
                evidence.id,
                evidence.kind,
                evidence.content_type or '',
                evidence.size or '',
                evidence.created_at.isoformat(),
                evidence.correlation_id or '',
                ','.join(evidence.tags) if evidence.tags else '',
                evidence.file_url or '',
                evidence.storage_url or ''
            ])

        csv_content = buffer.getvalue()
        buffer.close()

        response = Response(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="evidence_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        return response

    def _export_zip(self, queryset, include_files):
        """Export evidence as ZIP archive."""
        import zipfile
        from io import BytesIO

        buffer = BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add metadata file
            metadata = {
                'export_timestamp': timezone.now().isoformat(),
                'total_count': queryset.count(),
                'include_files': include_files,
                'evidence': []
            }

            for evidence in queryset:
                evidence_data = EvidenceSerializer(evidence).data
                metadata['evidence'].append(evidence_data)

                # Add file if requested and available
                if include_files and evidence.file and evidence.file.path:
                    try:
                        # Create a safe filename
                        safe_name = f"{evidence.id}_{evidence.kind}"
                        if evidence.file.name:
                            ext = evidence.file.name.split('.')[-1] if '.' in evidence.file.name else ''
                            if ext:
                                safe_name += f".{ext}"

                        zip_file.write(evidence.file.path, f"files/{safe_name}")
                    except Exception as e:
                        logger.warning(f"Failed to add file {evidence.id} to ZIP: {e}")

            # Add metadata as JSON file
            import json
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2, default=str))

        buffer.seek(0)
        response = Response(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="evidence_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.zip"'
        return response