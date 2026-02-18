# Copy data from blog editor tables to editor_* tables,
# add FK constraints (including FK to core_user), then drop old tables.

from django.db import migrations


def _reset_sequence(cursor, table):
    cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
    seq = cursor.fetchone()[0]
    if seq:
        cursor.execute(
            f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {table}), 1))",
            [seq],
        )


def forwards(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    # --- 1. Create parent tables (no FKs to other blog tables) ---
    for old, new in [
        ("blog_category", "editor_category"),
        ("blog_series", "editor_series"),
    ]:
        cursor.execute(f"CREATE TABLE {new} (LIKE {old} INCLUDING ALL)")
        cursor.execute(f"INSERT INTO {new} SELECT * FROM {old}")
        _reset_sequence(cursor, new)

    # --- 2. Create post table ---
    cursor.execute("CREATE TABLE editor_post (LIKE blog_post INCLUDING ALL)")
    cursor.execute("INSERT INTO editor_post SELECT * FROM blog_post")
    _reset_sequence(cursor, "editor_post")

    # --- 3. Create postseries table ---
    cursor.execute(
        "CREATE TABLE editor_postseries (LIKE blog_postseries INCLUDING ALL)"
    )
    cursor.execute("INSERT INTO editor_postseries SELECT * FROM blog_postseries")
    _reset_sequence(cursor, "editor_postseries")

    # --- 4. Add FK constraints ---
    fks = [
        # editor_post FKs
        ("editor_post", "author_id", "core_user"),
        ("editor_post", "category_id", "editor_category"),
        # editor_postseries FKs
        ("editor_postseries", "post_id", "editor_post"),
        ("editor_postseries", "series_id", "editor_series"),
    ]
    for tbl, col, ref in fks:
        cursor.execute(
            f"ALTER TABLE {tbl} ADD CONSTRAINT {tbl}_{col}_fk "
            f"FOREIGN KEY ({col}) REFERENCES {ref}(id) "
            f"DEFERRABLE INITIALLY DEFERRED"
        )

    # --- 5. Drop old tables (children first) ---
    cursor.execute("DROP TABLE blog_postseries CASCADE")
    cursor.execute("DROP TABLE blog_post CASCADE")
    cursor.execute("DROP TABLE blog_category CASCADE")
    cursor.execute("DROP TABLE blog_series CASCADE")


class Migration(migrations.Migration):
    dependencies = [
        ("editor", "0002_update_content_types"),
        ("core", "0002_copy_blog_user_to_core_user"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(name="category", table="editor_category"),
                migrations.AlterModelTable(name="series", table="editor_series"),
                migrations.AlterModelTable(name="post", table="editor_post"),
                migrations.AlterModelTable(
                    name="postseries", table="editor_postseries"
                ),
            ],
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
        ),
    ]
