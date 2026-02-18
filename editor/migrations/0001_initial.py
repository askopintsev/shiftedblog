# Generated manually: editor app uses existing blog_* tables (state only)

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("taggit", "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Category",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_category"},
                ),
                migrations.CreateModel(
                    name="Series",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_series"},
                ),
                migrations.CreateModel(
                    name="Post",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=250)),
                        ("slug", models.SlugField(max_length=250, unique=True)),
                        ("cover_image_credits", models.CharField(blank=True, default=None, max_length=250, null=True)),
                        ("cover_description", models.CharField(blank=True, default=None, max_length=250, null=True)),
                        ("body", models.TextField()),
                        ("published", models.DateTimeField(blank=True, default=None, null=True)),
                        ("created", models.DateTimeField(auto_now_add=True)),
                        ("updated", models.DateTimeField(auto_now=True)),
                        ("status", models.CharField(choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=10)),
                        ("cover_image", models.ImageField(upload_to="img/post/%Y/%m/%d")),
                        ("short_description", models.CharField(blank=True, default=None, max_length=300, null=True)),
                        ("views", models.PositiveIntegerField(default=0, verbose_name="Views count")),
                        ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="blog_posts", to=settings.AUTH_USER_MODEL)),
                        ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blog_category", to="editor.category")),
                        ("series", models.ManyToManyField(blank=True, related_name="blog_series", through="editor.PostSeries", to="editor.series")),
                        ("tags", taggit.managers.TaggableManager(help_text="A comma-separated list of tags.", through="taggit.TaggedItem", to="taggit.Tag", verbose_name="Tags")),
                    ],
                    options={"db_table": "blog_post", "ordering": ("-published", "-created")},
                ),
                migrations.CreateModel(
                    name="PostSeries",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("order_position", models.PositiveIntegerField(blank=True, default=None, null=True, verbose_name="Order position in series")),
                        ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="post_series", to="editor.post")),
                        ("series", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="series_posts", to="editor.series")),
                    ],
                    options={"db_table": "blog_postseries"},
                ),
            ],
            database_operations=[],
        ),
    ]
