from django.db import migrations
from django.utils.text import slugify


def _tag_slug(name: str, suffix: int | None = None) -> str:
    from unidecode import unidecode

    slug = slugify(unidecode(name or ""))
    if suffix is not None:
        slug = f"{slug}_{suffix}"
    return slug


def transliterate_tag_slugs(apps, schema_editor) -> None:
    Tag = apps.get_model("taggit", "Tag")

    for tag in Tag.objects.all().order_by("pk"):
        tag.slug = f"tag-migrate-{tag.pk}"
        tag.save(update_fields=["slug"])

    used: set[str] = set()
    for tag in Tag.objects.all().order_by("pk"):
        candidate = _tag_slug(tag.name)
        suffix = 2
        while not candidate or candidate in used:
            candidate = _tag_slug(tag.name, suffix)
            suffix += 1
        used.add(candidate)
        tag.slug = candidate
        tag.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("editor", "0012_category_slug"),
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
    ]

    operations = [
        migrations.RunPython(transliterate_tag_slugs, migrations.RunPython.noop),
    ]
