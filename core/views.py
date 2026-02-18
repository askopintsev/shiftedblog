import datetime
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect


def custom_page_not_found_view(request, exception):
    return render(request, "core/errors/404.html", {})


def custom_error_view(request, exception=None):
    return render(request, "core/errors/500.html", {})


def custom_permission_denied_view(request, exception=None):
    return render(request, "core/errors/403.html", {})


def custom_bad_request_view(request, exception=None):
    return render(request, "core/errors/400.html", {})


@csrf_protect
def custom_image_upload(request):
    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"]
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        date_path = datetime.datetime.now().strftime("%Y/%m/%d")
        filename = f"img/post/{date_path}/{uploaded_file.name}"
        file_path = default_storage.save(filename, ContentFile(uploaded_file.read()))

        url = f"{settings.MEDIA_URL}{file_path}"
        return JsonResponse(
            {
                "url": url,
                "uploaded": 1,
                "fileName": uploaded_file.name,
                "filePath": file_path,
            }
        )

    return JsonResponse({"error": "Invalid request"}, status=400)


def robots_txt(request):
    """Dynamic robots.txt view that uses settings for admin URL and site URL."""
    admin_url = getattr(settings, "ADMIN_URL", "mellon")
    site_url = getattr(settings, "SITE_URL", "http://localhost")

    content = f"""User-agent: *
Allow: /
Disallow: /{admin_url}/
Disallow: /account/
Disallow: /drafts/

Sitemap: {site_url}/sitemap.xml
    """

    return HttpResponse(content, content_type="text/plain")
