import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0010_post_optional_meta_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostHistory",
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
                ("title", models.CharField(blank=True, default="", max_length=250)),
                ("body", models.TextField()),
                (
                    "short_description",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=300,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="editor.post",
                    ),
                ),
            ],
            options={
                "verbose_name": "Post history",
                "verbose_name_plural": "Post history",
                "db_table": "editor_posthistory",
                "ordering": ["-created_at"],
            },
        ),
    ]
