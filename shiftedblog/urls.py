"""shiftedblog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView
from two_factor.urls import urlpatterns as tf_urlpatterns

import core.urls  # noqa: F401 - loads admin site customization
from core.views import (
    custom_image_upload,
    robots_txt,
)
from editor.sitemap import PostSitemap
from shiftedblog.rate_limited_views import (
    RateLimitedLoginView,
    RateLimitedQRGeneratorView,
    RateLimitedSetupView,
)

sitemaps = {"posts": PostSitemap}

zen_html_file = settings.DZEN_VERIFICATION_FILE

# Admin URL path (configurable via ADMIN_URL environment variable)
# Defaults to 'mellon' for backward compatibility
admin_url = getattr(settings, "ADMIN_URL", "mellon")

urlpatterns = [
    path("custom-image-upload/", custom_image_upload, name="custom_image_upload"),
    # path("ckeditor5/", include('django_ckeditor_5.urls')),
    path(f"{admin_url}/", admin.site.urls),
    path("", include("team.urls")),
    path("", include("editor.urls", namespace="editor")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # Rate-limited authentication endpoints (override two_factor URLs)
    path("login/", RateLimitedLoginView.as_view(), name="login"),
    path("account/login/", RateLimitedLoginView.as_view(), name="account_login"),
    path("account/two_factor/setup/", RateLimitedSetupView.as_view(), name="setup"),
    path("account/two_factor/qrcode/", RateLimitedQRGeneratorView.as_view(), name="qr"),
    # two_factor.urls: (pattern_list, 'two_factor'); include() needs 2-tuple
    path("", include((tf_urlpatterns[0], tf_urlpatterns[1]))),
    path("robots.txt", robots_txt),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.DZEN_VERIFICATION_FILE:
    urlpatterns.append(
        path(
            settings.DZEN_VERIFICATION_FILE,
            TemplateView.as_view(
                template_name=f"static_html/{settings.DZEN_VERIFICATION_FILE}"
            ),
            name="zen_static_page",
        )
    )

handler400 = "core.views.custom_bad_request_view"
handler403 = "core.views.custom_permission_denied_view"
handler404 = "core.views.custom_page_not_found_view"
handler500 = "core.views.custom_error_view"
