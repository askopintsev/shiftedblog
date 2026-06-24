"""Core request middleware."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

_DEV_CANONICAL_HOST = "localhost"
_DEV_ALTERNATE_HOSTS = frozenset({"0.0.0.0", "127.0.0.1", "[::1]"})


class DevCanonicalHostMiddleware:
    """Redirect alternate dev hosts to localhost so auth cookies are shared."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if settings.IS_PRODUCTION:
            return self.get_response(request)

        if request.path.startswith("/api/"):
            return self.get_response(request)

        host = request.get_host()
        hostname = host.split(":", 1)[0].lower()
        if hostname not in _DEV_ALTERNATE_HOSTS:
            return self.get_response(request)

        port = host.split(":", 1)[1] if ":" in host else ""
        canonical_host = _DEV_CANONICAL_HOST if not port else f"{_DEV_CANONICAL_HOST}:{port}"
        target = f"{request.scheme}://{canonical_host}{request.get_full_path()}"
        return HttpResponseRedirect(target)
