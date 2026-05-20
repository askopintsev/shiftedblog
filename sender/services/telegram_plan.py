"""Build a Telegram publish plan (text chunks, cover, galleries) before API calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage

from editor.models import Post
from sender.services.telegram_format import (
    build_formatted_message,
    extract_img_srcs_from_html,
    html_contains_link,
)

MAX_MESSAGE_LEN = 4096
MAX_CAPTION_LEN = 1024
MAX_MEDIA_GROUP = 10
CONTINUATION_PREFIX = "⏫ продолжение поста"


def _media_url_prefixes() -> list[str]:
    media = (getattr(settings, "MEDIA_URL", "") or "/media/").strip()
    if not media.startswith("/"):
        media = "/" + media
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    prefixes = [media, media.rstrip("/")]
    if base:
        prefixes.append(f"{base}{media}")
        prefixes.append(f"{base}{media.rstrip('/')}")
    return prefixes


def storage_path_from_src(src: str) -> str | None:
    """Map ``/media/...`` or absolute URL to a storage-relative path."""
    s = (src or "").strip()
    if not s:
        return None
    path = urlparse(s).path or "" if s.startswith(("http://", "https://")) else s
    for prefix in _media_url_prefixes():
        if path.startswith(prefix):
            rel = path[len(prefix) :].lstrip("/")
            return rel or None
    if path.startswith("img/"):
        return path
    return None


def collect_body_image_paths(post: Post) -> list[str]:
    """Inline ``<img>`` plus gallery rows, in stable order without duplicates."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(path: str | None) -> None:
        if not path or path in seen:
            return
        if not default_storage.exists(path):
            return
        seen.add(path)
        ordered.append(path)

    for src in extract_img_srcs_from_html(post.body or ""):
        add(storage_path_from_src(src))

    for gi in post.gallery_images.order_by(  # pyright: ignore[reportAttributeAccessIssue]
        "gallery_key",
        "order",
        "id",
    ):
        if gi.image:
            add(gi.image.name)

    return ordered


@dataclass(slots=True)
class TelegramPlannedStep:
    """One logical send step (may trigger multiple Bot API calls)."""

    text: str = ""
    cover_path: str | None = None
    media_paths: list[str] = field(default_factory=list)
    is_continuation: bool = False

    def preview_label(self) -> str:
        if self.is_continuation:
            return "Продолжение"
        if self.cover_path:
            return "Первый пост (обложка)"
        return "Пост"


@dataclass(slots=True)
class TelegramPublishPlan:
    steps: list[TelegramPlannedStep] = field(default_factory=list)
    has_subscription: bool = False

    @property
    def is_series(self) -> bool:
        return len(self.steps) > 1 or any(s.is_continuation for s in self.steps)


def _continuation_header() -> str:
    return f"{CONTINUATION_PREFIX}\n\n"


def _split_text_chunks(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text] if text else []
    chunks: list[str] = []
    rest = text
    header = _continuation_header()
    first = True
    while rest:
        limit = max_len if first else max_len - len(header)
        if len(rest) <= limit:
            chunk = rest
            rest = ""
        else:
            cut = rest[:limit]
            split_at = cut.rfind("\n\n")
            if split_at < limit // 3:
                split_at = cut.rfind("\n")
            if split_at < limit // 3:
                split_at = limit
            chunk = rest[:split_at].rstrip()
            rest = rest[split_at:].lstrip()
        if not first:
            chunk = header + chunk
        chunks.append(chunk)
        first = False
    return chunks


def _distribute_images(
    text_parts: list[str],
    image_paths: list[str],
) -> list[list[str]]:
    if not image_paths or not text_parts:
        return [[] for _ in text_parts]
    eligible = [i for i, part in enumerate(text_parts) if not html_contains_link(part)]
    targets = (
        eligible
        if eligible and len(eligible) < len(text_parts)
        else list(
            range(len(text_parts)),
        )
    )
    buckets: list[list[str]] = [[] for _ in text_parts]
    if not targets:
        return buckets
    per = max(1, (len(image_paths) + len(targets) - 1) // len(targets))
    idx = 0
    for t_i, target in enumerate(targets):
        if t_i < len(targets) - 1:
            take = image_paths[idx : idx + per]
        else:
            take = image_paths[idx:]
        buckets[target].extend(take)
        idx += len(take)
    return buckets


def _chunk_media(paths: list[str]) -> list[list[str]]:
    if not paths:
        return []
    return [
        paths[i : i + MAX_MEDIA_GROUP] for i in range(0, len(paths), MAX_MEDIA_GROUP)
    ]


def build_telegram_plan(post: Post, *, has_subscription: bool) -> TelegramPublishPlan:
    """Compose steps for *post* according to subscription and length rules."""
    full_text = build_formatted_message(post)
    cover_path: str | None = None
    if post.cover_image:
        cover_path = post.cover_image.name

    body_images = collect_body_image_paths(post)
    text_parts = _split_text_chunks(full_text, MAX_MESSAGE_LEN)
    if not text_parts and cover_path:
        text_parts = [""]

    image_buckets = _distribute_images(text_parts, body_images)
    steps: list[TelegramPlannedStep] = []

    single_text = len(text_parts) == 1
    for i, part_text in enumerate(text_parts):
        is_first = i == 0
        media_for_step = image_buckets[i] if i < len(image_buckets) else []
        step = TelegramPlannedStep(
            text=part_text,
            cover_path=cover_path if is_first else None,
            media_paths=[],
            is_continuation=not is_first,
        )
        steps.append(step)

        if single_text and not has_subscription:
            step.media_paths = body_images
        elif not single_text:
            step.media_paths = media_for_step

    if single_text and has_subscription:
        steps[0].media_paths = body_images

    return TelegramPublishPlan(steps=steps, has_subscription=has_subscription)


def build_preview_payload(plan: TelegramPublishPlan) -> list[dict[str, Any]]:
    """JSON-serializable preview rows for the admin UI."""
    rows: list[dict[str, Any]] = []
    for step in plan.steps:
        media_chunks = _chunk_media(step.media_paths)
        rows.append(
            {
                "label": step.preview_label(),
                "text": step.text,
                "has_cover": bool(step.cover_path),
                "media_count": len(step.media_paths),
                "media_groups": len(media_chunks),
                "is_continuation": step.is_continuation,
            },
        )
    return rows


def caption_for_step(
    step: TelegramPlannedStep,
    *,
    has_subscription: bool,
) -> str | None:
    """Caption for cover photo when text is sent together with the image."""
    if not step.cover_path or not step.text or has_subscription:
        return None
    if len(step.text) <= MAX_CAPTION_LEN:
        return step.text
    return None
