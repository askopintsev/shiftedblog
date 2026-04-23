import re

from django import template
from django.utils.html import strip_tags

register = template.Library()


@register.filter
def striptags_preserve_paragraphs(value):
    """
    Strip HTML tags but preserve paragraph structure by converting
    <p> and </p> tags to double newlines before stripping.
    This ensures that linebreaks filter can properly create <p> tags.
    """
    if not value:
        return ""

    value = re.sub(r"</p>\s*<p[^>]*>", "\n\n", str(value))
    value = re.sub(r"<p[^>]*>", "\n\n", value)
    value = re.sub(r"</p>", "", value)
    value = re.sub(
        r"</(?:div|section|article|blockquote|li|h[1-6])>",
        "\n\n",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = strip_tags(value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = value.strip()
    return value


@register.filter
def preview_inline_space(value):
    """Turn paragraph/line breaks into single spaces for one-line card previews."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


@register.filter
def truncatechars_whole_words(value, arg):
    """
    Truncate to at most ``arg`` characters; if the cut falls inside a word,
    include the rest of that word. Appends an ellipsis when text is shortened.
    """
    try:
        max_len = int(arg)
    except (ValueError, TypeError):
        return value

    if not value:
        return ""

    text = str(value).strip()
    if max_len <= 0:
        return ""

    if len(text) <= max_len:
        return text

    # Do not rstrip before extension: a cut like "aaa " + "bbb" must not become
    # "aaa" + "bbb" glued together (space was only after max_len).
    truncated = text[:max_len]
    if max_len < len(text):
        next_ch = text[max_len]
        if (
            next_ch
            and not next_ch.isspace()
            and truncated
            and not truncated[-1].isspace()
        ):
            j = max_len
            while j < len(text) and not text[j].isspace():
                truncated += text[j]
                j += 1
        truncated = truncated.rstrip()
        if truncated != text:
            truncated += "\u2026"

    return truncated


@register.filter
def truncatewords_preserve_newlines(value, arg):
    """Truncate text to a certain number of words while preserving newlines."""
    try:
        num_words = int(arg)
    except (ValueError, TypeError):
        return value

    if not value:
        return ""

    paragraphs = value.split("\n\n")
    result_paragraphs = []
    word_count = 0

    for para in paragraphs:
        if not para.strip():
            continue
        words = para.split()
        para_word_count = len(words)
        if word_count + para_word_count <= num_words:
            result_paragraphs.append(para)
            word_count += para_word_count
        else:
            remaining_words = num_words - word_count
            if remaining_words > 0:
                truncated_para = " ".join(words[:remaining_words])
                result_paragraphs.append(truncated_para)
            break

    return "\n\n".join(result_paragraphs)


@register.filter
def reading_time(value):
    """Calculate approximate reading time in minutes based on word count."""
    if not value:
        return 1
    text = strip_tags(str(value))
    word_count = len(text.split())
    minutes = max(1, round(word_count / 200))
    return minutes


@register.filter
def add_space_after_period(value):
    """Add a space after each period when followed by a letter (Latin/Cyrillic)."""
    if not value:
        return ""
    value = str(value)
    result = re.sub(r"\.([a-zA-Zа-яА-ЯёЁ])", r". \1", value)
    return result


@register.filter
def first_sentence(value):
    """Return first sentence from HTML/text content."""
    if not value:
        return ""

    text = strip_tags(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    parts = re.split(r"(?<=[.!?…])\s+", text, maxsplit=1)
    return parts[0].strip()
