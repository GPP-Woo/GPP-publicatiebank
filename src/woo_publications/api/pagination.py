from rest_framework.pagination import (
    CursorPagination as DRFCursorPagination,
    PageNumberPagination,
)


class DynamicPageSizePagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
    page_size = 10


class CursorPagination(DRFCursorPagination):
    page_size = 100

    def get_ordering(self, request, queryset, view):
        ordering_field = getattr(view, "pagination_ordering", self.ordering)

        return (ordering_field,)
