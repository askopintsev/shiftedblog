"""Convert editor HTML to Telegram HTML and build the outbound message template."""

from __future__ import annotations

import logging
import re
from html import escape
from html.parser import HTMLParser

from editor.models import Post

logger = logging.getLogger(__name__)

# Telegram Bot API HTML subset (parse_mode=HTML).
_TG_ALLOWED: frozenset[str] = frozenset(
    {
        "b",
        "strong",
        "i",
        "em",
        "u",
        "ins",
        "s",
        "strike",
        "del",
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
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "figure",
        "figcaption",
    }
)

_BALANCE_TAGS: frozenset[str] = frozenset(
    {"b", "i", "u", "s", "a", "code", "pre", "blockquote"},
)

_GALLERY_PLACEHOLDER_RE = re.compile(r"\[gallery:\d+\]", re.IGNORECASE)
_IMG_SRC_RE = re.compile(
    r"""<img[^>]+src=["']([^"']+)["']""",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"<a\s+href=", re.IGNORECASE)
_TAG_TOKEN_RE = re.compile(r"</?([a-zA-Z]+)(?:\s[^>]*)?>", re.IGNORECASE)
# Telegram shows paragraph gaps reliably with a blank line (double newline).
_BLOCK_BREAK = "\n\n"
_LINE_BREAK = "\n"


def escape_telegram_html(text: str) -> str:
    return escape(text or "", quote=False)


def balance_telegram_html(html: str) -> str:
    """Close any unclosed Telegram HTML tags so parse_mode=HTML is accepted."""
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
            # Drop stray closing tags.
        else:
            stack.append(tag)
            parts.append(token)
        pos = match.end()
    parts.append(html[pos:])
    for tag in reversed(stack):
        parts.append(f"</{tag}>")
    return "".join(parts)


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
    text = re.sub(r"<h[1-6](\s[^>]*)?>", "<h3>", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "</h3>", text, flags=re.IGNORECASE)
    return text


def format_tags_line(post: Post) -> str:
    """One line: ``#tag`` tokens separated by spaces."""
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
    if tag_l == "strong":
        return "b"
    if tag_l == "em":
        return "i"
    if tag_l == "ins":
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
        self._pending_h3_break = False
        self._in_pre = False

    def get_html(self) -> str:
        return balance_telegram_html("".join(self._out).strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "br":
            self._out.append(_LINE_BREAK)
            return
        if tag_l == "h3":
            self._pending_h3_break = True
            self._open_tag("b")
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
            self._open_tag(tg)

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l == "h3":
            self._close_tag("b")
            self._out.append(_BLOCK_BREAK)
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
            self._close_tag(tg)
            if tag_l == "blockquote":
                self._out.append(_BLOCK_BREAK)
            return
        if tag_l in _BLOCK_BREAK_TAGS:
            self._out.append(_BLOCK_BREAK)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._pending_h3_break:
            self._out.append(_BLOCK_BREAK)
            self._pending_h3_break = False
        self._out.append(escape_telegram_html(data))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")

    def _open_tag(self, tag: str) -> None:
        self._out.append(f"<{tag}>")
        self._tag_stack.append(tag)

    def _close_tag(self, tag: str) -> None:
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
    cleaned = _GALLERY_PLACEHOLDER_RE.sub("", cleaned)
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

        return escape_telegram_html(strip_tags(cleaned))
    text = parser.get_html()
    text = re.sub(r"\n{3,}", _BLOCK_BREAK, text)
    return text.strip()


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
    return balance_telegram_html(message)


def truncate_telegram_html(text: str, max_len: int) -> str:
    """Truncate HTML for Telegram captions without leaving tags open."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    split_at = cut.rfind("\n\n")
    if split_at < max_len // 3:
        split_at = cut.rfind("\n")
    if split_at < max_len // 3:
        split_at = max_len
    trimmed = cut[:split_at].rstrip()
    return balance_telegram_html(trimmed)
