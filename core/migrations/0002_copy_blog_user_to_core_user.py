# Copy data from blog_user tables to core_user tables, update content types,
# repoint third-party FK references, then drop old tables.

from django.db import migrations


def _reset_sequence(cursor, table):
    """Reset auto-increment sequence to current MAX(id)."""
    cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
    seq = cursor.fetchone()[0]
    if seq:
        cursor.execute(
            f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {table}), 1))",
            [seq],
        )


def _repoint_fks(cursor, old_table, new_table, exclude=None):
    """Find all FK constraints referencing old_table and repoint them to new_table."""
    exclude = set(exclude or [])
    cursor.execute(
        """
        SELECT cl.relname, a.attname, c.conname
        FROM pg_constraint c
        JOIN pg_class cl ON cl.oid = c.conrelid
        JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
        JOIN pg_namespace n ON n.oid = cl.relnamespace
        WHERE c.confrelid = %s::regclass
            AND c.contype = 'f'
            AND n.nspname = 'public'
        """,
        [old_table],
    )
    for tbl, col, constraint in cursor.fetchall():
        if tbl in exclude:
            continue
        cursor.execute(f'ALTER TABLE "{tbl}" DROP CONSTRAINT "{constraint}"')
        cursor.execute(
            f'ALTER TABLE "{tbl}" ADD CONSTRAINT "{tbl}_{col}_{new_table}_fk" '
            f'FOREIGN KEY ("{col}") REFERENCES "{new_table}"("id") '
            f"DEFERRABLE INITIALLY DEFERRED"
        )


def forwards(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    # --- 1. Update content type so all references follow automatically ---
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="blog", model="user").update(app_label="core")

    # --- 2. Create new tables and copy data ---
    for old, new in [
        ("blog_user", "core_user"),
        ("blog_user_groups", "core_user_groups"),
        ("blog_user_user_permissions", "core_user_user_permissions"),
    ]:
        cursor.execute(f"CREATE TABLE {new} (LIKE {old} INCLUDING ALL)")
        cursor.execute(f"INSERT INTO {new} SELECT * FROM {old}")
        _reset_sequence(cursor, new)

    # --- 3. Add FK constraints to new M2M tables ---
    m2m_fks = [
        ("core_user_groups", "user_id", "core_user"),
        ("core_user_groups", "group_id", "auth_group"),
        ("core_user_user_permissions", "user_id", "core_user"),
        ("core_user_user_permissions", "permission_id", "auth_permission"),
    ]
    for tbl, col, ref in m2m_fks:
        cursor.execute(
            f"ALTER TABLE {tbl} ADD CONSTRAINT {tbl}_{col}_fk "
            f"FOREIGN KEY ({col}) REFERENCES {ref}(id) "
            f"DEFERRABLE INITIALLY DEFERRED"
        )

    # --- 4. Repoint third-party FKs (django_admin_log, otp, etc.) ---
    _repoint_fks(
        cursor,
        "blog_user",
        "core_user",
        exclude={
            "blog_user_groups",
            "blog_user_user_permissions",
            "core_user_groups",
            "core_user_user_permissions",
        },
    )

    # --- 5. Drop old tables (data already copied) ---
    cursor.execute("DROP TABLE blog_user_user_permissions CASCADE")
    cursor.execute("DROP TABLE blog_user_groups CASCADE")
    cursor.execute("DROP TABLE blog_user CASCADE")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(name="user", table="core_user"),
            ],
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
        ),
    ]
