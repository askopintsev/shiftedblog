"""Build a Telegram publish plan (text chunks, cover, galleries) before API calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import default_storage

from editor.models import Post
from sender.services.telegram_format import (
    balance_telegram_html,
    build_formatted_message,
    extract_img_srcs_from_html,
    find_telegram_html_split_index,
    format_tags_suffix,
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

    if post.pk is None:
        return ordered

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


def _find_split_index(text: str, max_len: int, *, min_chunk_ratio: float = 1 / 3) -> int:
    return find_telegram_html_split_index(
        text,
        max_len,
        min_chunk_ratio=min_chunk_ratio,
    )


def _split_for_cover_caption(
    full_text: str,
    *,
    first_reserve: int = 0,
) -> tuple[str, str]:
    """First part fits a photo caption; remainder is sent as follow-up message(s)."""
    if not full_text:
        return "", ""
    limit = max(1, MAX_CAPTION_LEN - first_reserve)
    split_at = _find_split_index(full_text, limit)
    caption = balance_telegram_html(full_text[:split_at].rstrip())
    remainder = full_text[split_at:].lstrip()
    return caption, remainder


def _append_tags_to_part(parts: list[str], index: int, *, tags_suffix: str, tags_line: str) -> None:
    if not parts or not tags_line:
        return
    if parts[index]:
        parts[index] += tags_suffix
    else:
        parts[index] = tags_line


def _append_tags_to_series_endpoints(
    parts: list[str],
    *,
    tags_suffix: str,
    tags_line: str,
) -> None:
    if not parts or not tags_line:
        return
    _append_tags_to_part(parts, 0, tags_suffix=tags_suffix, tags_line=tags_line)
    if len(parts) > 1:
        _append_tags_to_part(parts, -1, tags_suffix=tags_suffix, tags_line=tags_line)


def _split_text_chunks(
    text: str,
    max_len: int,
    *,
    continuation_from_start: bool = False,
    first_chunk_reserve: int = 0,
    last_chunk_reserve: int = 0,
) -> list[str]:
    if not text:
        return []
    header = _continuation_header()
    first = not continuation_from_start
    header_len = 0 if first else len(header)
    base_limit = max(1, max_len - header_len)
    single_tag_reserve = 0 if continuation_from_start else first_chunk_reserve
    if len(text) + single_tag_reserve <= base_limit and first:
        return [text]
    chunks: list[str] = []
    rest = text
    first = not continuation_from_start
    while rest:
        header_len = 0 if first else len(header)
        base_limit = max(1, max_len - header_len)
        is_only_remaining = len(rest) + last_chunk_reserve <= base_limit
        if is_only_remaining:
            limit = max(1, base_limit - last_chunk_reserve)
            if first:
                limit = max(1, limit - first_chunk_reserve)
            if len(rest) <= limit:
                chunk = rest
                rest = ""
            else:
                split_at = _find_split_index(rest, limit)
                chunk = balance_telegram_html(rest[:split_at].rstrip())
                rest = rest[split_at:].lstrip()
        else:
            limit = max(1, base_limit - (first_chunk_reserve if first else 0))
            split_at = _find_split_index(rest, limit)
            chunk = balance_telegram_html(rest[:split_at].rstrip())
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


def media_preview_url(storage_path: str | None) -> str | None:
    """Public URL for a stored image path (admin Telegram preview)."""
    if not storage_path:
        return None
    if not default_storage.exists(storage_path):
        return None
    return default_storage.url(storage_path)


def _preview_urls(paths: list[str]) -> list[str]:
    urls: list[str] = []
    for path in paths:
        url = media_preview_url(path)
        if url:
            urls.append(url)
    return urls


def build_telegram_plan(post: Post, *, has_subscription: bool) -> TelegramPublishPlan:
    """Compose steps for *post* according to subscription and length rules."""
    tags_suffix, tags_line, tags_reserve = format_tags_suffix(post)
    core_text = build_formatted_message(post, include_tags=False)
    cover_path: str | None = None
    if post.cover_image:
        cover_path = post.cover_image.name

    body_images = collect_body_image_paths(post)
    text_parts: list[str]
    if (
        cover_path
        and not has_subscription
        and core_text
        and len(core_text) + tags_reserve > MAX_CAPTION_LEN
    ):
        caption_part, remainder = _split_for_cover_caption(
            core_text,
            first_reserve=tags_reserve,
        )
        text_parts = [caption_part]
        if remainder:
            text_parts.extend(
                _split_text_chunks(
                    remainder,
                    MAX_MESSAGE_LEN,
                    continuation_from_start=True,
                    last_chunk_reserve=tags_reserve,
                ),
            )
    else:
        text_parts = _split_text_chunks(
            core_text,
            MAX_MESSAGE_LEN,
            first_chunk_reserve=tags_reserve,
            last_chunk_reserve=tags_reserve,
        )
    _append_tags_to_series_endpoints(
        text_parts,
        tags_suffix=tags_suffix,
        tags_line=tags_line,
    )
    if not text_parts and cover_path:
        text_parts = [tags_line or ""]

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


def caption_for_step(
    step: TelegramPlannedStep,
    *,
    has_subscription: bool,
) -> str | None:
    """Caption for cover photo when text is sent together with the image."""
    if not step.cover_path or not step.text or has_subscription:
        return None
    return step.text


def text_dispatches_for_step(
    step: TelegramPlannedStep,
    *,
    has_subscription: bool,
) -> list[tuple[str, str]]:
    """Exact ``(kind, text)`` payloads sent to Telegram (caption / message)."""
    caption = caption_for_step(step, has_subscription=has_subscription)
    dispatches: list[tuple[str, str]] = []
    text_as_caption = caption is not None and caption == step.text
    if caption:
        dispatches.append(("caption", caption))
    if step.text and not text_as_caption:
        dispatches.append(("message", step.text))
    return dispatches


def _limit_note_for_photo(
    step: TelegramPlannedStep,
    *,
    has_subscription: bool,
    caption: str | None,
    step_total: int = 1,
) -> str:
    if not step.cover_path:
        return ""
    if has_subscription and step.text:
        return (
            "Premium layout: cover is sent without caption; "
            "text follows as a separate message."
        )
    if caption and step_total > 1:
        return (
            f"Caption ends at the last complete sentence "
            f"(max {MAX_CAPTION_LEN} characters); remainder in the next message."
        )
    if caption:
        return f"Text fits in photo caption (max {MAX_CAPTION_LEN} characters)."
    return "Cover photo without caption."


def build_preview_send_cards(plan: TelegramPublishPlan) -> list[dict[str, Any]]:
    """One preview card per Bot API send, in publish order."""
    cards: list[dict[str, Any]] = []
    has_sub = plan.has_subscription
    step_total = len(plan.steps)

    for step_idx, step in enumerate(plan.steps, start=1):
        dispatches = text_dispatches_for_step(step, has_subscription=has_sub)
        caption = next((text for kind, text in dispatches if kind == "caption"), None)
        message = next((text for kind, text in dispatches if kind == "message"), None)
        media_chunks = _chunk_media(step.media_paths)

        if step.cover_path:
            cards.append(
                {
                    "step_index": step_idx,
                    "step_total": step_total,
                    "step_label": step.preview_label(),
                    "step_is_continuation": step.is_continuation,
                    "kind": "photo",
                    "title": "sendPhoto (cover)",
                    "text": caption or "",
                    "has_text": bool(caption),
                    "char_count": len(caption) if caption else 0,
                    "max_chars": MAX_CAPTION_LEN if caption else None,
                    "limit_note": _limit_note_for_photo(
                        step,
                        has_subscription=has_sub,
                        caption=caption,
                        step_total=step_total,
                    ),
                    "cover_url": media_preview_url(step.cover_path),
                    "thumb_urls": [],
                    "image_count": 1,
                },
            )

        if message:
            cards.append(
                {
                    "step_index": step_idx,
                    "step_total": step_total,
                    "step_label": step.preview_label(),
                    "step_is_continuation": step.is_continuation,
                    "kind": "message",
                    "title": "sendMessage",
                    "text": message,
                    "has_text": True,
                    "char_count": len(message),
                    "max_chars": MAX_MESSAGE_LEN,
                    "limit_note": f"Message limit {MAX_MESSAGE_LEN} characters.",
                    "cover_url": None,
                    "thumb_urls": [],
                    "image_count": 0,
                },
            )

        for chunk_idx, chunk in enumerate(media_chunks, start=1):
            thumb_urls = _preview_urls(chunk)
            cards.append(
                {
                    "step_index": step_idx,
                    "step_total": step_total,
                    "step_label": step.preview_label(),
                    "step_is_continuation": step.is_continuation,
                    "kind": "media_group",
                    "title": "sendMediaGroup",
                    "text": "",
                    "has_text": False,
                    "char_count": 0,
                    "max_chars": None,
                    "limit_note": (
                        f"Album {chunk_idx}/{len(media_chunks)} — "
                        f"up to {MAX_MEDIA_GROUP} photos per send."
                    ),
                    "cover_url": None,
                    "thumb_urls": thumb_urls,
                    "image_count": len(thumb_urls),
                    "media_group_index": chunk_idx,
                    "media_group_total": len(media_chunks),
                },
            )

    send_total = len(cards)
    for send_index, card in enumerate(cards, start=1):
        card["send_index"] = send_index
        card["send_total"] = send_total

    return cards


def build_preview_payload(plan: TelegramPublishPlan) -> dict[str, Any]:
    """Preview metadata and sequential send cards for the admin UI."""
    cards = build_preview_send_cards(plan)
    return {
        "has_subscription": plan.has_subscription,
        "is_series": plan.is_series,
        "step_count": len(plan.steps),
        "send_count": len(cards),
        "cards": cards,
    }
