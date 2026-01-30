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

    # Convert <p> and </p> tags to double newlines to preserve paragraph breaks
    # Handle </p><p> pattern first (adjacent paragraphs)
    value = re.sub(r"</p>\s*<p[^>]*>", "\n\n", str(value))
    # Handle opening <p> tags
    value = re.sub(r"<p[^>]*>", "\n\n", value)
    # Handle closing </p> tags
    value = re.sub(r"</p>", "", value)

    # Also handle <br> and <br/> tags as single newlines
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)

    # Now strip all remaining HTML tags
    value = strip_tags(value)

    # Clean up excessive newlines (more than 2 consecutive)
    value = re.sub(r"\n{3,}", "\n\n", value)

    # Strip leading/trailing whitespace but preserve internal structure
    value = value.strip()

    return value


@register.filter
def truncatewords_preserve_newlines(value, arg):
    """
    Truncate text to a certain number of words while preserving newlines.
    This is needed because Django's truncatewords removes newlines.
    """
    try:
        num_words = int(arg)
    except (ValueError, TypeError):
        return value

    if not value:
        return ""

    # Split by double newlines (paragraphs) to preserve structure
    paragraphs = value.split("\n\n")
    result_paragraphs = []
    word_count = 0

    for para in paragraphs:
        if not para.strip():
            continue

        words = para.split()
        para_word_count = len(words)

        if word_count + para_word_count <= num_words:
            # Include the whole paragraph
            result_paragraphs.append(para)
            word_count += para_word_count
        else:
            # Add partial paragraph if there's room
            remaining_words = num_words - word_count
            if remaining_words > 0:
                truncated_para = " ".join(words[:remaining_words])
                result_paragraphs.append(truncated_para)
            break

    return "\n\n".join(result_paragraphs)


@register.filter
def reading_time(value):
    """
    Calculate approximate reading time in minutes based on word count.
    Assumes average reading speed of 200 words per minute.
    """
    if not value:
        return 1

    # Strip HTML tags to get plain text
    text = strip_tags(str(value))
    # Count words
    word_count = len(text.split())
    # Calculate minutes (200 words per minute)
    minutes = max(1, round(word_count / 200))
    return minutes


@register.filter
def add_space_after_period(value):
    """
    Add a space after each period (.) when followed by a letter (character).
    Supports both Latin and Cyrillic letters.
    """
    if not value:
        return ""

    value = str(value)
    # Add space after period if followed by a letter (both Latin and Cyrillic)
    # Pattern: period followed by a letter (a-z, A-Z, а-я, А-Я, ё, Ё, etc.)  # noqa: RUF003
    result = re.sub(r"\.([a-zA-Zа-яА-ЯёЁ])", r". \1", value)  # noqa: RUF001

    return result
