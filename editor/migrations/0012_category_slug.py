from django.db import migrations, models
from django.utils.text import slugify


def _legacy_segment(name: str, pk: int) -> str:
    raw = (name or "").strip()
    if raw:
        segment = slugify(raw)
        if segment:
            return segment
    return f"cat-{pk}"


def populate_category_slugs(apps, schema_editor) -> None:
    Category = apps.get_model("editor", "Category")
    # Legacy nav slugs → category display names (one-time migration mapping).
    preferred_by_name = {
        "блог": "blog",
        "blog": "blog",
        "проекты": "projects",
        "projects": "projects",
    }

    used: set[str] = set()
    for category in Category.objects.all().order_by("pk"):
        name = (category.name or "").strip()
        slug = preferred_by_name.get(name.lower(), "")
        if not slug:
            slug = _legacy_segment(name, category.pk)
        base = slug
        suffix = 2
        while slug in used:
            slug = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        category.slug = slug
        category.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("editor", "0011_post_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.RunPython(populate_category_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(max_length=100, unique=True),
        ),
    ]
