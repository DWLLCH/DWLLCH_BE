from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CommonPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "size"

    def get_paginated_response(self, data):
        return Response({
            "content": data,
            "page": self.page.number - 1,
            "size": self.get_page_size(self.request),
            "totalElements": self.page.paginator.count,
            "totalPages": self.page.paginator.num_pages,
            "hasNext": self.page.has_next(),
        })

    def get_page_number(self, request, paginator):
        page_number = request.query_params.get(self.page_query_param, 0)
        try:
            page_number = int(page_number) + 1
        except (TypeError, ValueError):
            page_number = 1
        return page_number