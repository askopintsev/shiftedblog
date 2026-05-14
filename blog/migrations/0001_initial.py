from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("editor", "0008_post_slug_redirect"),
    ]

    operations = [
        migrations.CreateModel(
            name="SitePublication",
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
                ("published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "post",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="site_publication",
                        to="editor.post",
                    ),
                ),
            ],
            options={
                "ordering": ("-published_at",),
            },
        ),
        migrations.AddIndex(
            model_name="sitepublication",
            index=models.Index(fields=["published_at"], name="blog_sitepub_pubat_idx"),
        ),
    ]
