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
    ordering = "-pk"

    def get_paginated_response_schema(self, schema):
        """
        TODO remove this overwrite once DRF has tackled the following issue:
        https://github.com/encode/django-rest-framework/discussions/10095
        """
        response_schema = super().get_paginated_response_schema(schema)

        response_schema["properties"]["next"]["example"] = (
            f"http://api.example.org/accounts/?{self.cursor_query_param}=cD00ODY%3D"
        )

        return response_schema
