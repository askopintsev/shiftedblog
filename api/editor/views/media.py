"""Media upload API."""

from __future__ import annotations

import datetime
import os
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.media_urls import relative_media_path
from api.editor.permissions import IsStaffUser

_VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff")
_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
}


def _extension_for_upload(name: str, content_type: str) -> str | None:
    ext = os.path.splitext(name or "")[1].lower()
    if ext in _VALID_EXTENSIONS:
        return ext
    inferred = _EXT_BY_CONTENT_TYPE.get((content_type or "").lower())
    if inferred in _VALID_EXTENSIONS:
        return inferred
    return None


def _safe_upload_basename(name: str, ext: str) -> str:
    stem = os.path.splitext(os.path.basename(name or ""))[0].strip()
    if not stem or stem in {".", ".."}:
        stem = f"clipboard-{uuid.uuid4().hex[:12]}"
    return f"{stem}{ext}"


class MediaUploadView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get("upload") or request.FILES.get("file")
        if not uploaded:
            return Response({"error": "Invalid request"}, status=400)
        content_type = getattr(uploaded, "content_type", "") or ""
        ext = _extension_for_upload(uploaded.name, content_type)
        if ext is None:
            return Response({"error": "Unsupported file type"}, status=400)
        basename = _safe_upload_basename(uploaded.name, ext)
        date_path = datetime.datetime.now().strftime("%Y/%m/%d")
        filename = f"img/post/{date_path}/{basename}"
        file_path = default_storage.save(filename, ContentFile(uploaded.read()))
        url = relative_media_path(default_storage.url(file_path))
        return Response(
            {
                "url": url,
                "uploaded": 1,
                "fileName": basename,
                "filePath": file_path,
            },
        )
