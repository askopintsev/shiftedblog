# Optional title/slug/author/cover/category; body stays required at DB level.

import django.db.models.deletion
import editor.models.post
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0009_alter_post_cover_image_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="title",
            field=models.CharField(blank=True, default="", max_length=250),
        ),
        migrations.AlterField(
            model_name="post",
            name="slug",
            field=models.SlugField(blank=True, default="", max_length=250, unique=True),
        ),
        migrations.AlterField(
            model_name="post",
            name="author",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="blog_posts",
                to="core.user",
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="blog_category",
                to="editor.category",
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="cover_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="img/post/%Y/%m/%d",
                validators=[editor.models.post.validate_image_extension],
            ),
        ),
    ]
