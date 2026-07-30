"""Convert editor HTML to Telegram Bot API 10.1 rich-message HTML."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html import escape, unescape
from html.parser import HTMLParser

from editor.models import Post
from sender.services.telegram_format import (
    _GALLERY_PLACEHOLDER_RE,
    _NBSP_CHARS_RE,
    _ZWSP_RE,
    escape_telegram_html,
    format_tags_line,
)

logger = logging.getLogger(__name__)

MAX_RICH_MESSAGE_LEN = 32768
MAX_RICH_MEDIA = 50

ResolveStoragePath = Callable[[str], str | None]

_RICH_BALANCE_TAGS: frozenset[str] = frozenset(
    {
        "b",
        "i",
        "u",
        "s",
        "a",
        "code",
        "pre",
        "blockquote",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "mark",
        "sub",
        "sup",
        "details",
        "summary",
        "figure",
        "figcaption",
    }
)

_RICH_INLINE_TAGS: frozenset[str] = frozenset(
    {"b", "i", "u", "s", "a", "code", "mark", "sub", "sup"},
)

_TAG_TOKEN_RE = re.compile(r"</?([a-zA-Z]+)(?:\s[^>]*)?>", re.IGNORECASE)


@dataclass(slots=True)
class RichMediaAttachment:
    """Local file attached to a rich message via ``tg://photo?id=``."""

    media_id: str
    storage_path: str


@dataclass(slots=True)
class RichMessagePayload:
    """HTML body plus optional uploaded media for ``sendRichMessage``."""

    html: str = ""
    media: list[RichMediaAttachment] = field(default_factory=list)

    @property
    def inline_storage_paths(self) -> list[str]:
        return [item.storage_path for item in self.media]


def normalize_editor_html_for_rich(html: str) -> str:
    """Map common CKEditor markup to semantic HTML (keep heading tags)."""
    if not html:
        return ""
    text = html
    text = re.sub(
        r"<span[^>]*font-weight\s*:\s*(?:bold|[6-9]00)[^>]*>(.*?)</span>",
        r"<strong>\1</strong>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<span[^>]*font-style\s*:\s*italic[^>]*>(.*?)</span>",
        r"<em>\1</em>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<span[^>]*text-decoration\s*:\s*underline[^>]*>(.*?)</span>",
        r"<u>\1</u>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<span[^>]*text-decoration\s*:\s*line-through[^>]*>(.*?)</span>",
        r"<s>\1</s>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<span[^>]*>(.*?)</span>",
        r"\1",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<pre>\s*<code[^>]*>", "<pre>", text, flags=re.IGNORECASE)
    text = re.sub(r"</code>\s*</pre>", "</pre>", text, flags=re.IGNORECASE)
    return text


def _normalize_plain_text(text: str) -> str:
    if not text:
        return ""
    value = str(text)
    for _ in range(3):
        decoded = unescape(value)
        if decoded == value:
            break
        value = decoded
    value = re.sub(r"&nbsp;", " ", value, flags=re.IGNORECASE)
    value = _NBSP_CHARS_RE.sub(" ", value)
    value = _ZWSP_RE.sub("", value)
    return value


def _strip_gallery_placeholders(html: str) -> str:
    if not html:
        return ""
    return _GALLERY_PLACEHOLDER_RE.sub("", html)


def _map_inline_tag(tag_l: str) -> str | None:
    if tag_l in ("strike", "del"):
        return "s"
    if tag_l in ("strong", "b"):
        return "b"
    if tag_l in ("em", "i"):
        return "i"
    if tag_l in ("ins", "u"):
        return "u"
    if tag_l in _RICH_INLINE_TAGS:
        return tag_l
    return None


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    name_l = name.lower()
    for key, val in attrs:
        if key.lower() == name_l and val:
            return val.strip()
    return ""


def balance_telegram_rich_html(html: str) -> str:
    """Close any unclosed rich-message HTML tags."""
    if not html:
        return ""
    stack: list[str] = []
    parts: list[str] = []
    pos = 0
    for match in _TAG_TOKEN_RE.finditer(html):
        parts.append(html[pos : match.start()])
        token = match.group(0)
        tag = (match.group(1) or "").lower()
        if tag not in _RICH_BALANCE_TAGS:
            parts.append(token)
        elif token.startswith("</"):
            if stack and stack[-1] == tag:
                stack.pop()
                parts.append(token)
        else:
            stack.append(tag)
            parts.append(token)
        pos = match.end()
    parts.append(html[pos:])
    for tag in reversed(stack):
        parts.append(f"</{tag}>")
    return "".join(parts)


def sanitize_telegram_rich_html(html: str) -> str:
    """Normalize output to Telegram rich-message HTML."""
    if not html:
        return ""

    text = html
    text = re.sub(r"<strong\b[^>]*>", "<b>", text, flags=re.IGNORECASE)
    text = re.sub(r"</strong>", "</b>", text, flags=re.IGNORECASE)
    text = re.sub(r"<em\b[^>]*>", "<i>", text, flags=re.IGNORECASE)
    text = re.sub(r"</em>", "</i>", text, flags=re.IGNORECASE)
    text = re.sub(r"<ins\b[^>]*>", "<u>", text, flags=re.IGNORECASE)
    text = re.sub(r"</ins>", "</u>", text, flags=re.IGNORECASE)
    text = re.sub(r"<(?:strike|del)\b[^>]*>", "<s>", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:strike|del)>", "</s>", text, flags=re.IGNORECASE)

    for tag in _RICH_INLINE_TAGS:
        while True:
            merged = re.sub(
                rf"<{tag}>\s*<{tag}>",
                f"<{tag}>",
                text,
                flags=re.IGNORECASE,
            )
            merged = re.sub(
                rf"</{tag}>\s*</{tag}>",
                f"</{tag}>",
                merged,
                flags=re.IGNORECASE,
            )
            if merged == text:
                break
            text = merged

    for tag in _RICH_INLINE_TAGS:
        text = re.sub(rf"<{tag}>(\s*)</{tag}>", r"\1", text, flags=re.IGNORECASE)

    return balance_telegram_rich_html(text.strip())


def rich_photo_tag(media_id: str, *, caption: str = "") -> str:
    """Return a rich HTML photo block for ``tg://photo?id=``."""
    safe_id = escape(media_id, quote=True)
    img = f'<img src="tg://photo?id={safe_id}">'
    caption = (caption or "").strip()
    if not caption:
        return img
    safe_caption = escape_telegram_html(caption)
    return f"<figure>{img}<figcaption>{safe_caption}</figcaption></figure>"


class _TelegramRichHTMLConverter(HTMLParser):
    """Walk editor HTML and emit Telegram rich-message HTML with media blocks."""

    def __init__(
        self,
        *,
        resolve_storage_path: ResolveStoragePath | None = None,
        media_id_prefix: str = "img",
        max_media: int = MAX_RICH_MEDIA,
        skip_storage_paths: set[str] | None = None,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._tag_stack: list[str] = []
        self._in_pre = False
        self._resolve = resolve_storage_path
        self._media_id_prefix = media_id_prefix
        self._max_media = max_media
        self._skip_paths = skip_storage_paths or set()
        self.media: list[RichMediaAttachment] = []
        self._figure_depth = 0
        self._figure_src = ""
        self._figure_alt = ""
        self._figure_caption_parts: list[str] = []
        self._in_figcaption = False

    def get_html(self) -> str:
        return sanitize_telegram_rich_html("".join(self._out).strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "figure":
            self._figure_depth += 1
            self._figure_src = ""
            self._figure_alt = ""
            self._figure_caption_parts = []
            self._in_figcaption = False
            return
        if self._figure_depth:
            if tag_l == "img":
                self._figure_src = _attr(attrs, "src")
                self._figure_alt = _attr(attrs, "alt")
            elif tag_l == "figcaption":
                self._in_figcaption = True
            return
        if tag_l == "img":
            self._emit_photo(
                src=_attr(attrs, "src"),
                caption=_attr(attrs, "alt"),
            )
            return
        if tag_l == "br":
            self._out.append("<br>")
            return
        if tag_l == "hr":
            self._out.append("<hr>")
            return
        if tag_l.startswith("h") and len(tag_l) == 2 and tag_l[1].isdigit():
            self._open_block(tag_l)
            return
        if tag_l == "pre":
            self._in_pre = True
            self._open_block("pre")
            return
        if tag_l == "code" and self._in_pre:
            return
        if tag_l == "a":
            href = _attr(attrs, "href")
            if href:
                safe_href = escape(href, quote=True)
                self._out.append(f'<a href="{safe_href}">')
                self._tag_stack.append("a")
            return
        if tag_l in ("ul", "ol", "table", "thead", "tbody", "tr", "blockquote"):
            self._open_block(tag_l)
            return
        if tag_l in ("p", "li", "th", "td", "details", "summary"):
            attr_bits: list[str] = []
            if tag_l == "td":
                for key, val in attrs:
                    key_l = key.lower()
                    if key_l in ("colspan", "rowspan") and val:
                        attr_bits.append(f'{key_l}="{escape(str(val), quote=True)}"')
            if attr_bits:
                self._out.append(f"<{tag_l} {' '.join(attr_bits)}>")
                self._tag_stack.append(tag_l)
            else:
                self._open_block(tag_l)
            return
        tg = _map_inline_tag(tag_l)
        if tg:
            self._open_inline(tg)

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l == "figure":
            if self._figure_depth:
                self._figure_depth -= 1
                if self._figure_depth == 0:
                    caption = "".join(self._figure_caption_parts).strip()
                    if not caption:
                        caption = self._figure_alt
                    self._emit_photo(src=self._figure_src, caption=caption)
                    self._figure_src = ""
                    self._figure_alt = ""
                    self._figure_caption_parts = []
                    self._in_figcaption = False
            return
        if self._figure_depth:
            if tag_l == "figcaption":
                self._in_figcaption = False
            return
        if tag_l == "img":
            return
        if tag_l == "code" and self._in_pre:
            return
        if tag_l == "pre":
            self._close_block("pre")
            self._in_pre = False
            return
        if tag_l == "a":
            self._close_inline("a")
            return
        if tag_l in (
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "blockquote",
            "details",
            "summary",
        ):
            self._close_block(tag_l)
            return
        tg = _map_inline_tag(tag_l)
        if tg:
            self._close_inline(tg)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._figure_depth:
            if self._in_figcaption:
                self._figure_caption_parts.append(_normalize_plain_text(data))
            return
        self._out.append(escape_telegram_html(_normalize_plain_text(data)))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(unescape(f"&#{name};"))

    def _emit_photo(self, *, src: str, caption: str = "") -> None:
        if not src or self._resolve is None:
            return
        if len(self.media) >= self._max_media:
            return
        path = self._resolve(src)
        if not path or path in self._skip_paths:
            return
        if any(item.storage_path == path for item in self.media):
            # Still show duplicate references via the same media id.
            media_id = next(
                item.media_id for item in self.media if item.storage_path == path
            )
        else:
            media_id = f"{self._media_id_prefix}{len(self.media) + 1}"
            self.media.append(RichMediaAttachment(media_id=media_id, storage_path=path))
        self._close_all_open_tags()
        self._out.append(rich_photo_tag(media_id, caption=caption))

    def _close_all_open_tags(self) -> None:
        while self._tag_stack:
            open_tag = self._tag_stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == "pre":
                self._in_pre = False

    def _open_block(self, tag: str) -> None:
        self._out.append(f"<{tag}>")
        self._tag_stack.append(tag)

    def _close_block(self, tag: str) -> None:
        if tag not in self._tag_stack:
            return
        while self._tag_stack:
            open_tag = self._tag_stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == tag:
                return

    def _open_inline(self, tag: str) -> None:
        self._out.append(f"<{tag}>")
        self._tag_stack.append(tag)

    def _close_inline(self, tag: str) -> None:
        if tag not in self._tag_stack:
            return
        while self._tag_stack:
            open_tag = self._tag_stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == tag:
                return


def html_body_to_telegram_rich_html(
    html: str,
    *,
    resolve_storage_path: ResolveStoragePath | None = None,
    skip_storage_paths: set[str] | None = None,
    max_media: int = MAX_RICH_MEDIA,
) -> RichMessagePayload:
    """Convert body HTML to rich-message HTML; keep single images as media blocks."""
    if not html:
        return RichMessagePayload()
    cleaned = normalize_editor_html_for_rich(html)
    cleaned = _strip_gallery_placeholders(cleaned)
    parser = _TelegramRichHTMLConverter(
        resolve_storage_path=resolve_storage_path,
        skip_storage_paths=skip_storage_paths,
        max_media=max_media,
    )
    try:
        parser.feed(cleaned)
        parser.close()
    except Exception:
        logger.warning(
            "Telegram rich HTML conversion failed; using plain fallback",
            exc_info=True,
        )
        from django.utils.html import strip_tags

        plain = _normalize_plain_text(strip_tags(cleaned))
        return RichMessagePayload(
            html=sanitize_telegram_rich_html(f"<p>{escape_telegram_html(plain)}</p>"),
        )
    return RichMessagePayload(html=parser.get_html(), media=parser.media)


def build_formatted_rich_message(
    post: Post,
    *,
    include_tags: bool = True,
    cover_path: str | None = None,
    resolve_storage_path: ResolveStoragePath | None = None,
) -> RichMessagePayload:
    """Rich template: optional cover photo, ``<h1>`` title, body, tags."""
    parts: list[str] = []
    media: list[RichMediaAttachment] = []
    skip_paths: set[str] = set()

    if cover_path:
        media.append(RichMediaAttachment(media_id="cover", storage_path=cover_path))
        parts.append(rich_photo_tag("cover"))
        skip_paths.add(cover_path)

    title = (post.title or "").strip()
    if title:
        parts.append(f"<h1>{escape_telegram_html(title)}</h1>")

    remaining_slots = max(0, MAX_RICH_MEDIA - len(media))
    body_payload = html_body_to_telegram_rich_html(
        post.body or "",
        resolve_storage_path=resolve_storage_path,
        skip_storage_paths=skip_paths,
        max_media=remaining_slots,
    )
    if body_payload.html:
        parts.append(body_payload.html)
    media.extend(body_payload.media)

    if include_tags:
        tags_line = format_tags_line(post)
        if tags_line:
            parts.append(f"<p>{tags_line}</p>")

    return RichMessagePayload(
        html=sanitize_telegram_rich_html("\n".join(parts)),
        media=media,
    )


def prepare_outbound_telegram_rich_html(text: str) -> str:
    """Final pass before ``sendRichMessage``."""
    return sanitize_telegram_rich_html(text)


def find_telegram_rich_html_split_index(
    text: str,
    max_len: int,
    *,
    min_chunk_ratio: float = 1 / 3,
) -> int:
    """Return split position after the last block boundary within *max_len*."""
    if len(text) <= max_len:
        return len(text)
    window = text[:max_len]
    min_pos = int(max_len * min_chunk_ratio)
    for token in (
        "</p>",
        "</h1>",
        "</h2>",
        "</h3>",
        "</li>",
        "</blockquote>",
        "</figure>",
        ">",  # end of standalone <img ...> media block
    ):
        # Prefer structural closes; for ">" only accept after tg://photo img tags.
        if token == ">":
            pos = window.rfind("tg://photo?id=")
            if pos >= min_pos:
                end = window.find(">", pos)
                if end != -1 and end < max_len:
                    return end + 1
            continue
        pos = window.rfind(token)
        if pos >= min_pos:
            return pos + len(token)
    split_at = window.rfind("\n\n")
    if split_at < min_pos:
        split_at = max_len
    return split_at
