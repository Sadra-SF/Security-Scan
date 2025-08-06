import django_filters
from django.db.models import Q
from findings.models import Finding


class FindingFilter(django_filters.FilterSet):
    project = django_filters.UUIDFilter(method="filter_project")
    target = django_filters.UUIDFilter(field_name="target_id")
    scan = django_filters.UUIDFilter(field_name="scan_id")
    severity = django_filters.CharFilter(field_name="severity", lookup_expr="iexact")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    category = django_filters.CharFilter(method="filter_category")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Finding
        fields = ["project", "target", "scan", "severity", "status"]

    def filter_project(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(target__project_id=value)

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        # stored in metadata.category or infer from title prefix "Category: name"
        return queryset.filter(
            Q(metadata__category__iexact=value) | Q(title__istartswith=f"{value}:")
        )

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(description__icontains=value)
            | Q(locations__icontains=value)
        )