import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_post_body_segments(post):
    """
    Split post.body by [gallery:N] placeholders and return a list of segments.
    Each segment is a dict: {"type": "html", "content": "..."} or
    {"type": "gallery", "gallery_key": N, "gallery_images": list, "carousel_id": str}.
    Use in template to render body with galleries at user-defined positions.
    """
    body = post.body or ""
    # Split by [gallery:1], [gallery:2], etc.; capture the number
    parts = re.split(r"\[gallery:(\d+)\]", body)
    # parts = [html0, key1, html1, key2, html2, ...]
    segments = []
    all_images = list(post.gallery_images.all())
    images_by_key = {}
    for img in all_images:
        images_by_key.setdefault(img.gallery_key, []).append(img)
    carousel_counter = 0
    for i in range(len(parts)):
        if i % 2 == 0:
            if parts[i]:
                segments.append({"type": "html", "content": mark_safe(parts[i])})
        else:
            key = int(parts[i])
            gallery_images = images_by_key.get(key, [])
            carousel_counter += 1
            carousel_id = f"postgallery-{post.id}-{key}-{carousel_counter}"
            segments.append(
                {
                    "type": "gallery",
                    "gallery_key": key,
                    "gallery_images": gallery_images,
                    "carousel_id": carousel_id,
                }
            )
    return segments
