"""Convert editor HTML to Telegram HTML and build the outbound message template."""

from __future__ import annotations

import logging
import re
from html import escape, unescape
from html.parser import HTMLParser

from editor.models import Post

logger = logging.getLogger(__name__)

# Telegram Bot API HTML (parse_mode=HTML) — only these tags are valid.
_TG_ALLOWED: frozenset[str] = frozenset(
    {
        "b",
        "i",
        "u",
        "s",
        "a",
        "code",
        "pre",
        "blockquote",
    }
)

_BLOCK_BREAK_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "blockquote",
        "li",
        "tr",
        "figure",
        "figcaption",
    }
)

_BALANCE_TAGS: frozenset[str] = frozenset(
    {"b", "i", "u", "s", "a", "code", "pre", "blockquote"},
)

_NESTABLE_INLINE = frozenset({"b", "i", "u", "s"})

_GALLERY_PLACEHOLDER_RE = re.compile(r"\[gallery:\d+\]", re.IGNORECASE)
_NBSP_CHARS_RE = re.compile(r"[\u00a0\u202f]")
_ZWSP_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_IMG_SRC_RE = re.compile(
    r"""<img[^>]+src=["']([^"']+)["']""",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"<a\s+href=", re.IGNORECASE)
_TAG_TOKEN_RE = re.compile(r"</?([a-zA-Z]+)(?:\s[^>]*)?>", re.IGNORECASE)
_BLOCK_BREAK = "\n\n"
_LINE_BREAK = "\n"


def _normalize_telegram_plain_text(text: str) -> str:
    """Decode entities and drop editor artifacts from Telegram text nodes."""
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


def escape_telegram_html(text: str) -> str:
    return escape(text or "", quote=False)


def balance_telegram_html(html: str) -> str:
    """Close any unclosed Telegram HTML tags."""
    if not html:
        return ""
    stack: list[str] = []
    parts: list[str] = []
    pos = 0
    for match in _TAG_TOKEN_RE.finditer(html):
        parts.append(html[pos : match.start()])
        token = match.group(0)
        tag = (match.group(1) or "").lower()
        if tag not in _BALANCE_TAGS:
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


def _open_style_stack_at(text: str, position: int) -> list[tuple[str, int]]:
    """Return ``(tag, open_index)`` pairs for style tags open at *position*."""
    stack: list[tuple[str, int]] = []
    for match in _TAG_TOKEN_RE.finditer(text):
        if match.start() >= position:
            break
        tag = (match.group(1) or "").lower()
        if tag not in _BALANCE_TAGS:
            continue
        token = match.group(0)
        if token.startswith("</"):
            if stack and stack[-1][0] == tag:
                stack.pop()
        else:
            stack.append((tag, match.start()))
    return stack


def _nudge_split_out_of_tag_token(text: str, split_at: int) -> int:
    """Move a split that falls inside ``<...>`` to the tag opening."""
    for match in _TAG_TOKEN_RE.finditer(text):
        if match.start() < split_at < match.end():
            return match.start()
        if match.start() >= split_at:
            break
    return split_at


def _find_style_region_end(text: str, tag: str, open_start: int) -> int | None:
    """Return index after the closing tag matching *open_start*."""
    depth = 0
    for match in _TAG_TOKEN_RE.finditer(text, pos=open_start):
        current = (match.group(1) or "").lower()
        if current != tag:
            continue
        token = match.group(0)
        if token.startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
        else:
            depth += 1
    return None


def adjust_split_index_for_telegram_html(
    text: str,
    split_at: int,
    *,
    max_pos: int | None = None,
) -> int:
    """Move a split so styled HTML blocks are not cut in the middle."""
    if split_at <= 0 or split_at >= len(text):
        return split_at

    split_at = _nudge_split_out_of_tag_token(text, split_at)
    open_regions = _open_style_stack_at(text, split_at)
    if not open_regions:
        return split_at

    tag, style_start = open_regions[0]
    if style_start <= 0 or style_start >= split_at:
        if style_start != 0:
            return split_at
        region_end = _find_style_region_end(text, tag, style_start)
        if region_end is not None and region_end > split_at:
            if max_pos is None or region_end <= max_pos:
                return region_end
        return split_at

    return style_start


_SENTENCE_BREAKS = (
    ".\n\n",
    "!\n\n",
    "?\n\n",
    ". ",
    "! ",
    "? ",
    ".\n",
    "!\n",
    "?\n",
    "… ",
    "…\n",
)


def find_telegram_html_split_index(
    text: str,
    max_len: int,
    *,
    min_chunk_ratio: float = 1 / 3,
) -> int:
    """Return split position after the last sentence end within *max_len*."""
    if len(text) <= max_len:
        return len(text)
    window = text[:max_len]
    min_pos = int(max_len * min_chunk_ratio)
    best = -1
    for token in _SENTENCE_BREAKS:
        pos = window.rfind(token)
        if pos >= min_pos:
            best = max(best, pos + len(token))
    if best > 0:
        return adjust_split_index_for_telegram_html(
            text,
            best,
            max_pos=max_len,
        )
    split_at = window.rfind("\n\n")
    if split_at < min_pos:
        split_at = window.rfind("\n")
    if split_at < min_pos:
        split_at = max_len
    return adjust_split_index_for_telegram_html(
        text,
        split_at,
        max_pos=max_len,
    )


def sanitize_telegram_html(html: str) -> str:
    """Normalize output to Telegram-safe HTML (see Bot API formatting options)."""
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

    text = re.sub(r"<p[^>]*>\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*</p>", _BLOCK_BREAK, text, flags=re.IGNORECASE)
    text = re.sub(r"<div[^>]*>\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*</div>", _BLOCK_BREAK, text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", _LINE_BREAK, text, flags=re.IGNORECASE)

    for tag in _NESTABLE_INLINE:
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

    for tag in _NESTABLE_INLINE:
        # Keep whitespace-only tags as plain spaces (CKEditor often wraps word gaps).
        text = re.sub(rf"<{tag}>(\s*)</{tag}>", r"\1", text, flags=re.IGNORECASE)

    text = re.sub(r"\n{3,}", _BLOCK_BREAK, text)
    text = balance_telegram_html(text.strip())
    return text


def _convert_headings_to_telegram_blocks(html: str) -> str:
    """Headings → blank line + ``<b>title</b>`` + blank line."""

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1) or ""
        plain = re.sub(r"<[^>]+>", "", inner)
        plain = unescape(plain).strip()
        if not plain:
            return _BLOCK_BREAK
        return f"{_BLOCK_BREAK}<b>{escape_telegram_html(plain)}</b>{_BLOCK_BREAK}"

    return re.sub(
        r"<h[1-6][^>]*>(.*?)</h[1-6]>",
        repl,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def normalize_editor_html(html: str) -> str:
    """Map common CKEditor markup to Telegram-safe HTML before conversion."""
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
    return _convert_headings_to_telegram_blocks(text)


def format_tags_line(post: Post) -> str:
    """One line: ``#tag`` tokens separated by spaces."""
    if post.pk is None:
        return ""
    names = [t.name.strip() for t in post.tags.all() if (t.name or "").strip()]
    if not names:
        return ""
    parts: list[str] = []
    for name in names:
        token = re.sub(r"\s+", "_", name)
        token = re.sub(r"[^\w\u0400-\u04FF-]+", "", token, flags=re.UNICODE)
        if token:
            parts.append(f"#{escape_telegram_html(token)}")
    return " ".join(parts)


def format_tags_suffix(post: Post) -> tuple[str, str, int]:
    """Return ``(suffix_with_blank, bare_line, reserved_len)`` for the first send."""
    tags_line = format_tags_line(post)
    if not tags_line:
        return "", "", 0
    suffix = f"\n\n{tags_line}"
    return suffix, tags_line, len(suffix)


def extract_img_srcs_from_html(html: str) -> list[str]:
    """Return ``src`` values from ``<img>`` tags in document order."""
    if not html:
        return []
    return _IMG_SRC_RE.findall(html)


def html_contains_link(html: str) -> bool:
    return bool(_HREF_RE.search(html or ""))


def _map_tag_to_telegram(tag_l: str) -> str | None:
    if tag_l in ("strike", "del"):
        return "s"
    if tag_l in ("strong", "b"):
        return "b"
    if tag_l in ("em", "i"):
        return "i"
    if tag_l in ("ins", "u"):
        return "u"
    if tag_l in _TG_ALLOWED:
        return tag_l
    return None


class _TelegramHTMLConverter(HTMLParser):
    """Walk editor HTML and emit Telegram-compatible HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._tag_stack: list[str] = []
        self._in_pre = False

    def get_html(self) -> str:
        return sanitize_telegram_html("".join(self._out).strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "br":
            self._out.append(_LINE_BREAK)
            return
        if tag_l.startswith("h") and tag_l[1:].isdigit():
            return
        if tag_l == "img":
            return
        if tag_l in ("ul", "ol", "figure", "table"):
            return
        if tag_l == "li":
            self._out.append("• ")
            return
        if tag_l == "pre":
            self._in_pre = True
            self._open_tag("pre")
            return
        if tag_l == "code" and self._in_pre:
            return
        if tag_l == "a":
            href = ""
            for key, val in attrs:
                if key.lower() == "href" and val:
                    href = val.strip()
                    break
            if href:
                safe_href = escape(href, quote=True)
                self._out.append(f'<a href="{safe_href}">')
                self._tag_stack.append("a")
            return
        tg = _map_tag_to_telegram(tag_l)
        if tg:
            if tg in _NESTABLE_INLINE and tg in self._tag_stack:
                return
            self._open_tag(tg)

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l.startswith("h") and tag_l[1:].isdigit():
            return
        if tag_l == "img":
            return
        if tag_l in ("ul", "ol", "figure", "table", "li"):
            if tag_l == "li":
                self._out.append(_LINE_BREAK)
            return
        if tag_l == "code" and self._in_pre:
            return
        if tag_l == "pre":
            self._close_tag("pre")
            self._in_pre = False
            self._out.append(_BLOCK_BREAK)
            return
        if tag_l == "a":
            self._close_tag("a")
            return
        tg = _map_tag_to_telegram(tag_l)
        if tg:
            if tg in _NESTABLE_INLINE and tg not in self._tag_stack:
                return
            self._close_tag(tg)
            if tag_l == "blockquote":
                self._out.append(_BLOCK_BREAK)
            return
        if tag_l in _BLOCK_BREAK_TAGS:
            self._out.append(_BLOCK_BREAK)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._out.append(escape_telegram_html(_normalize_telegram_plain_text(data)))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(unescape(f"&#{name};"))

    def _open_tag(self, tag: str) -> None:
        self._out.append(f"<{tag}>")
        self._tag_stack.append(tag)

    def _close_tag(self, tag: str) -> None:
        if tag not in self._tag_stack:
            return
        while self._tag_stack:
            open_tag = self._tag_stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == tag:
                return


def html_body_to_telegram_html(html: str) -> str:
    """Strip galleries/figures and convert remaining HTML to Telegram HTML."""
    if not html:
        return ""
    cleaned = normalize_editor_html(html)
    cleaned = _strip_gallery_placeholders(cleaned)
    cleaned = re.sub(
        r"<figure[^>]*>.*?</figure>",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(r"<img[^>]*>", "", cleaned, flags=re.IGNORECASE)
    parser = _TelegramHTMLConverter()
    try:
        parser.feed(cleaned)
        parser.close()
    except Exception:
        logger.warning(
            "Telegram HTML conversion failed; using plain fallback",
            exc_info=True,
        )
        from django.utils.html import strip_tags

        plain = _normalize_telegram_plain_text(strip_tags(cleaned))
        return sanitize_telegram_html(escape_telegram_html(plain))
    return parser.get_html()


def build_formatted_message(post: Post, *, include_tags: bool = True) -> str:
    """Template: bold title, blank line, body, optional blank line + ``#tags``."""
    lines: list[str] = []
    title = (post.title or "").strip()
    if title:
        lines.append(f"<b>{escape_telegram_html(title)}</b>")
        lines.append("")
    body = html_body_to_telegram_html(post.body or "")
    if body:
        lines.append(body)
    if include_tags:
        tags_line = format_tags_line(post)
        if tags_line:
            if lines:
                lines.append("")
            lines.append(tags_line)
    message = "\n".join(lines).strip()
    return sanitize_telegram_html(message)


def truncate_telegram_html(text: str, max_len: int) -> str:
    """Truncate HTML for Telegram captions without leaving tags open."""
    if len(text) <= max_len:
        return text
    split_at = find_telegram_html_split_index(text, max_len)
    trimmed = text[:split_at].rstrip()
    return sanitize_telegram_html(balance_telegram_html(trimmed))


def prepare_outbound_telegram_html(text: str) -> str:
    """Final pass before Bot API send (caption or message text)."""
    return sanitize_telegram_html(text)
