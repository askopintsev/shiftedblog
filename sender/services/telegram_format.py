"""Convert editor HTML to Telegram HTML and build the outbound message template."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

from editor.models import Post

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

_GALLERY_PLACEHOLDER_RE = re.compile(r"\[gallery:\d+\]", re.IGNORECASE)
_IMG_SRC_RE = re.compile(
    r"""<img[^>]+src=["']([^"']+)["']""",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"<a\s+href=", re.IGNORECASE)
# Telegram shows paragraph gaps reliably with a blank line (double newline).
_BLOCK_BREAK = "\n\n"
_LINE_BREAK = "\n"


def escape_telegram_html(text: str) -> str:
    return escape(text or "", quote=False)


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

    def get_html(self) -> str:
        return "".join(self._out).strip()

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
    cleaned = _GALLERY_PLACEHOLDER_RE.sub("", html)
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
    return "\n".join(lines).strip()
