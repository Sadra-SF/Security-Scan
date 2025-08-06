import django_filters
from django.db.models import Q
from scans.models import Scan


class ScanFilter(django_filters.FilterSet):
    target = django_filters.UUIDFilter(field_name="target_id")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("started_at", "started_at"),
            ("created_at", "created_at"),
        )
    )

    class Meta:
        model = Scan
        fields = ["target", "status", "type", "scanner"]