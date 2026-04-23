"""Request middleware for the editor app."""

# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

from collections.abc import Callable

from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, resolve

from editor.models import Post


class PostDetailViewCountMiddleware:
    """Bump ``Post.views`` on GET for published posts (even when HTML is cached)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Use META so stubs match WSGI (avoids reportUnnecessaryComparison on .method).
        if request.META.get("REQUEST_METHOD") == "GET":
            try:
                match = resolve(request.path_info)
            except Resolver404:
                match = None
            if match is not None and match.view_name == "editor:post_detail":
                slug = match.kwargs.get("slug")
                if slug:
                    Post.objects.filter(slug=slug, status="published").update(
                        views=F("views") + 1
                    )
        return self.get_response(request)
