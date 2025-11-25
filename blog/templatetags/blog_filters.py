import re
from django import template
from django.utils.text import Truncator

register = template.Library()


@register.filter
def striptags_preserve_paragraphs(value):
    """
    Strip HTML tags but preserve paragraph structure by converting
    <p> and </p> tags to double newlines before stripping.
    This ensures that linebreaks filter can properly create <p> tags.
    """
    if not value:
        return ''
    
    # Convert <p> and </p> tags to double newlines to preserve paragraph breaks
    # Handle </p><p> pattern first (adjacent paragraphs)
    value = re.sub(r'</p>\s*<p[^>]*>', '\n\n', str(value))
    # Handle opening <p> tags
    value = re.sub(r'<p[^>]*>', '\n\n', value)
    # Handle closing </p> tags
    value = re.sub(r'</p>', '', value)
    
    # Also handle <br> and <br/> tags as single newlines
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.IGNORECASE)
    
    # Now strip all remaining HTML tags
    from django.utils.html import strip_tags
    value = strip_tags(value)
    
    # Clean up excessive newlines (more than 2 consecutive)
    value = re.sub(r'\n{3,}', '\n\n', value)
    
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
        return ''
    
    # Split by double newlines (paragraphs) to preserve structure
    paragraphs = value.split('\n\n')
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
                truncated_para = ' '.join(words[:remaining_words])
                result_paragraphs.append(truncated_para)
            break
    
    return '\n\n'.join(result_paragraphs)

