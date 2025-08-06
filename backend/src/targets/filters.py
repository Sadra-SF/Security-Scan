import django_filters
from django.db.models import Q
from targets.models import Target


class TargetFilter(django_filters.FilterSet):
    project = django_filters.UUIDFilter(field_name="project_id")
    is_active = django_filters.BooleanFilter(method="filter_is_active")
    type = django_filters.CharFilter(field_name="type", lookup_expr="iexact")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Target
        fields = ["project", "type", "slug", "name"]

    def filter_is_active(self, queryset, name, value):
        # Treat "active" as targets not soft-deleted; no deleted field exists, so passthrough
        # Kept for API compatibility; could later wire to a real field.
        return queryset if value is None else queryset

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(address__icontains=value))