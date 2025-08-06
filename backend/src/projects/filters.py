import django_filters
from projects.models import Project


class ProjectFilter(django_filters.FilterSet):
    organization = django_filters.UUIDFilter(field_name="organization_id")
    name = django_filters.CharFilter(field_name="name", lookup_expr="iexact")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Project
        fields = ["organization", "name", "slug", "visibility"]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            django_filters.filters.utils.q.Q(name__icontains=value)
            | django_filters.filters.utils.q.Q(slug__icontains=value)
        )