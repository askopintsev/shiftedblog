"""Media upload API."""

from __future__ import annotations

import datetime
import os

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.editor.media_urls import relative_media_path
from api.editor.permissions import IsStaffUser


class MediaUploadView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        uploaded = request.FILES.get("upload") or request.FILES.get("file")
        if not uploaded:
            return Response({"error": "Invalid request"}, status=400)
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"]
        ext = os.path.splitext(uploaded.name)[1].lower()
        if ext not in valid_extensions:
            return Response({"error": "Unsupported file type"}, status=400)
        date_path = datetime.datetime.now().strftime("%Y/%m/%d")
        filename = f"img/post/{date_path}/{uploaded.name}"
        file_path = default_storage.save(filename, ContentFile(uploaded.read()))
        url = relative_media_path(default_storage.url(file_path))
        return Response(
            {
                "url": url,
                "uploaded": 1,
                "fileName": uploaded.name,
                "filePath": file_path,
            },
        )
