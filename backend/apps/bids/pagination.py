from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Server-side pagination for every list endpoint (§13, §17). 575+ rows
    must never ship to the browser in one response."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
