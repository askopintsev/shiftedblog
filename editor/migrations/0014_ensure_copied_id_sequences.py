# LIKE … INCLUDING ALL copies SERIAL defaults that still point at the source
# table's sequence. Dropping blog_* then removes that sequence, so editor_*
# inserts store NULL in id. Recreate owned sequences for fresh/test databases.

from django.db import migrations

_COPIED_TABLES = (
    "editor_category",
    "editor_series",
    "editor_post",
    "editor_postseries",
)


def _ensure_id_sequence(cursor, table: str) -> None:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        [table],
    )
    if not cursor.fetchone()[0]:
        return

    cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
    seq = cursor.fetchone()[0]
    cursor.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{table}"')
    max_id = cursor.fetchone()[0]
    if seq:
        cursor.execute("SELECT setval(%s, %s, %s)", [seq, max(max_id, 1), max_id > 0])
        return

    seq_name = f"{table}_id_seq"
    cursor.execute(f'CREATE SEQUENCE IF NOT EXISTS "{seq_name}"')
    cursor.execute(
        f'ALTER TABLE "{table}" ALTER COLUMN id SET DEFAULT nextval(%s)',
        [seq_name],
    )
    cursor.execute(f'ALTER SEQUENCE "{seq_name}" OWNED BY "{table}".id')
    cursor.execute("SELECT setval(%s, %s, %s)", [seq_name, max(max_id, 1), max_id > 0])


def ensure_copied_id_sequences(apps, schema_editor) -> None:
    with schema_editor.connection.cursor() as cursor:
        for table in _COPIED_TABLES:
            _ensure_id_sequence(cursor, table)


class Migration(migrations.Migration):
    dependencies = [
        ("editor", "0013_tag_slugs_latin"),
    ]

    operations = [
        migrations.RunPython(ensure_copied_id_sequences, migrations.RunPython.noop),
    ]
