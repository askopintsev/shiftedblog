# Add PostGalleryImage for post body carousel gallery

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0003_copy_blog_tables_to_editor"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostGalleryImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "image",
                    models.ImageField(upload_to="img/post/gallery/%Y/%m/%d"),
                ),
                (
                    "caption",
                    models.CharField(blank=True, default="", max_length=250),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order in the carousel (lower first).",
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery_images",
                        to="editor.post",
                    ),
                ),
            ],
            options={
                "db_table": "editor_postgalleryimage",
                "ordering": ["order", "id"],
            },
        ),
    ]
