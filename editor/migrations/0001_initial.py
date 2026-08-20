# Generated manually: editor app uses existing blog_* tables (state only)

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


def _table_exists(schema_editor, table):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            [table],
        )
        return cursor.fetchone()[0]


def create_blog_editor_tables(apps, schema_editor):
    if _table_exists(schema_editor, "blog_category"):
        return

    schema_editor.execute(
        """
        CREATE TABLE blog_category (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            name VARCHAR(250) NOT NULL
        )
        """
    )
    schema_editor.execute(
        """
        CREATE TABLE blog_series (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            name VARCHAR(250) NOT NULL
        )
        """
    )
    schema_editor.execute(
        """
        CREATE TABLE blog_post (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            title VARCHAR(250) NOT NULL,
            slug VARCHAR(250) NOT NULL UNIQUE,
            cover_image_credits VARCHAR(250) NULL,
            cover_description VARCHAR(250) NULL,
            body TEXT NOT NULL,
            published TIMESTAMP WITH TIME ZONE NULL,
            created TIMESTAMP WITH TIME ZONE NOT NULL,
            updated TIMESTAMP WITH TIME ZONE NOT NULL,
            status VARCHAR(10) NOT NULL,
            cover_image VARCHAR(100) NOT NULL,
            short_description VARCHAR(300) NULL,
            views INTEGER NOT NULL CHECK (views >= 0),
            author_id BIGINT NOT NULL,
            category_id BIGINT NOT NULL,
            CONSTRAINT blog_post_author_id_fk
                FOREIGN KEY (author_id) REFERENCES blog_user (id)
                DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT blog_post_category_id_fk
                FOREIGN KEY (category_id) REFERENCES blog_category (id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )
    schema_editor.execute(
        """
        CREATE TABLE blog_postseries (
            id BIGSERIAL NOT NULL PRIMARY KEY,
            order_position INTEGER NULL CHECK (order_position >= 0),
            post_id BIGINT NOT NULL,
            series_id BIGINT NOT NULL,
            CONSTRAINT blog_postseries_post_id_fk
                FOREIGN KEY (post_id) REFERENCES blog_post (id)
                DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT blog_postseries_series_id_fk
                FOREIGN KEY (series_id) REFERENCES blog_series (id)
                DEFERRABLE INITIALLY DEFERRED
        )
        """
    )


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        (
            "taggit",
            "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Category",
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
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_category"},
                ),
                migrations.CreateModel(
                    name="Series",
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
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_series"},
                ),
                migrations.CreateModel(
                    name="Post",
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
                        ("title", models.CharField(max_length=250)),
                        ("slug", models.SlugField(max_length=250, unique=True)),
                        (
                            "cover_image_credits",
                            models.CharField(
                                blank=True, default=None, max_length=250, null=True
                            ),
                        ),
                        (
                            "cover_description",
                            models.CharField(
                                blank=True, default=None, max_length=250, null=True
                            ),
                        ),
                        ("body", models.TextField()),
                        (
                            "published",
                            models.DateTimeField(blank=True, default=None, null=True),
                        ),
                        ("created", models.DateTimeField(auto_now_add=True)),
                        ("updated", models.DateTimeField(auto_now=True)),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("draft", "Draft"),
                                    ("published", "Published"),
                                ],
                                default="draft",
                                max_length=10,
                            ),
                        ),
                        (
                            "cover_image",
                            models.ImageField(upload_to="img/post/%Y/%m/%d"),
                        ),
                        (
                            "short_description",
                            models.CharField(
                                blank=True, default=None, max_length=300, null=True
                            ),
                        ),
                        (
                            "views",
                            models.PositiveIntegerField(
                                default=0, verbose_name="Views count"
                            ),
                        ),
                        (
                            "author",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="blog_posts",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "category",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="blog_category",
                                to="editor.category",
                            ),
                        ),
                        (
                            "series",
                            models.ManyToManyField(
                                blank=True,
                                related_name="blog_series",
                                through="editor.PostSeries",
                                to="editor.series",
                            ),
                        ),
                        (
                            "tags",
                            taggit.managers.TaggableManager(
                                help_text="A comma-separated list of tags.",
                                through="taggit.TaggedItem",
                                to="taggit.Tag",
                                verbose_name="Tags",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "blog_post",
                        "ordering": ("-published", "-created"),
                    },
                ),
                migrations.CreateModel(
                    name="PostSeries",
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
                            "order_position",
                            models.PositiveIntegerField(
                                blank=True,
                                default=None,
                                null=True,
                                verbose_name="Order position in series",
                            ),
                        ),
                        (
                            "post",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="post_series",
                                to="editor.post",
                            ),
                        ),
                        (
                            "series",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="series_posts",
                                to="editor.series",
                            ),
                        ),
                    ],
                    options={"db_table": "blog_postseries"},
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    create_blog_editor_tables, migrations.RunPython.noop
                ),
            ],
        ),
    ]
