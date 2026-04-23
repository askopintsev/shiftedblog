"""Normalize uploads to AVIF/WebP (JPEG fallback) via Pillow — no external services."""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from PIL import Image, ImageOps, features

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile

_HAS_AVIF = bool(features.check("avif"))


def _max_edge() -> int:
    return int(getattr(settings, "IMAGE_UPLOAD_MAX_EDGE", 2560))


def _avif_quality() -> int:
    return int(getattr(settings, "IMAGE_UPLOAD_AVIF_QUALITY", 72))


def _webp_quality() -> int:
    return int(getattr(settings, "IMAGE_UPLOAD_WEBP_QUALITY", 85))


def _jpeg_quality() -> int:
    return int(getattr(settings, "IMAGE_UPLOAD_JPEG_QUALITY", 88))


def _is_new_upload(field_file: FieldFile) -> bool:
    if not field_file or not field_file.name:
        return False
    try:
        fh = field_file.file
    except (ValueError, OSError):
        return False
    return isinstance(fh, (InMemoryUploadedFile, TemporaryUploadedFile))


def _flatten_for_jpeg(im: Image.Image) -> Image.Image:
    if im.mode == "LA":
        im = im.convert("RGBA")
    if im.mode in ("RGBA",):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        alpha = im.split()[-1]
        bg.paste(im, mask=alpha)
        return bg
    if im.mode == "P" and "transparency" in im.info:
        return _flatten_for_jpeg(im.convert("RGBA"))
    return im.convert("RGB")


def _maybe_downscale(im: Image.Image) -> Image.Image:
    w, h = im.size
    m = max(w, h)
    cap = _max_edge()
    if m <= cap:
        return im
    scale = cap / m
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def _base_name(path: str) -> str:
    base = os.path.basename(path)
    stem, _ext = os.path.splitext(base)
    return stem or "image"


def _encode_delivery(im: Image.Image, stem: str) -> tuple[str, ContentFile]:
    """Return (filename, content) for AVIF, WebP, or JPEG."""
    buf = io.BytesIO()
    ext: str
    if _HAS_AVIF:
        try:
            im.save(
                buf,
                format="AVIF",
                quality=_avif_quality(),
                speed=int(getattr(settings, "IMAGE_UPLOAD_AVIF_SPEED", 6)),
            )
            ext = ".avif"
            buf.seek(0)
            return f"{stem}{ext}", ContentFile(buf.read())
        except Exception:
            buf = io.BytesIO()

    try:
        im.save(buf, format="WEBP", quality=_webp_quality(), method=6)
        ext = ".webp"
        buf.seek(0)
        return f"{stem}{ext}", ContentFile(buf.read())
    except Exception:
        buf = io.BytesIO()

    rgb = _flatten_for_jpeg(im)
    rgb.save(
        buf,
        format="JPEG",
        quality=_jpeg_quality(),
        optimize=True,
        progressive=True,
    )
    buf.seek(0)
    return f"{stem}.jpg", ContentFile(buf.read())


def normalize_image_field_file(
    instance,
    field_name: str,
    update_fields: set[str] | None,
) -> None:
    """New uploads → AVIF/WebP/JPEG; no-op for stored files or skipped saves."""
    if update_fields is not None and field_name not in update_fields:
        return
    field = getattr(instance, field_name)
    if not field:
        return
    if not _is_new_upload(field):
        return

    field.open("rb")
    try:
        raw = field.read()
    finally:
        field.close()

    with Image.open(io.BytesIO(raw)) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode == "CMYK":
            im = im.convert("RGB")
        im = _maybe_downscale(im)
        if im.mode not in ("RGB", "RGBA"):
            if im.mode in ("L", "LA"):
                im = im.convert("RGBA" if im.mode == "LA" else "RGB")
            else:
                im = im.convert("RGBA" if "transparency" in im.info else "RGB")

        stem = _base_name(field.name)
        filename, content = _encode_delivery(im, stem)
        field.save(filename, content, save=False)
