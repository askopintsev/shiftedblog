# Copy data from blog team tables to team_* tables, update content types,
# then drop old tables.

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

    # --- 1. Update content types ---
    ContentType = apps.get_model("contenttypes", "ContentType")
    model_names = ["person", "accountgroup", "account", "skillgroup", "skill"]
    ContentType.objects.filter(app_label="blog", model__in=model_names).update(
        app_label="team"
    )

    # --- 2. Create parent tables first (no FKs to other blog tables) ---
    for old, new in [
        ("blog_person", "team_person"),
        ("blog_accountgroup", "team_accountgroup"),
        ("blog_skillgroup", "team_skillgroup"),
    ]:
        cursor.execute(f"CREATE TABLE {new} (LIKE {old} INCLUDING ALL)")
        cursor.execute(f"INSERT INTO {new} SELECT * FROM {old}")
        _reset_sequence(cursor, new)

    # --- 3. Create child tables ---
    for old, new in [
        ("blog_account", "team_account"),
        ("blog_skill", "team_skill"),
    ]:
        cursor.execute(f"CREATE TABLE {new} (LIKE {old} INCLUDING ALL)")
        cursor.execute(f"INSERT INTO {new} SELECT * FROM {old}")
        _reset_sequence(cursor, new)

    # --- 4. Add FK constraints within team tables ---
    fks = [
        ("team_account", "group_id", "team_accountgroup"),
        ("team_account", "person_id", "team_person"),
        ("team_skill", "group_id", "team_skillgroup"),
        ("team_skill", "person_id", "team_person"),
    ]
    for tbl, col, ref in fks:
        cursor.execute(
            f"ALTER TABLE {tbl} ADD CONSTRAINT {tbl}_{col}_fk "
            f"FOREIGN KEY ({col}) REFERENCES {ref}(id) "
            f"DEFERRABLE INITIALLY DEFERRED"
        )

    # --- 5. Drop old tables (children first, then parents) ---
    cursor.execute("DROP TABLE blog_account CASCADE")
    cursor.execute("DROP TABLE blog_skill CASCADE")
    cursor.execute("DROP TABLE blog_person CASCADE")
    cursor.execute("DROP TABLE blog_accountgroup CASCADE")
    cursor.execute("DROP TABLE blog_skillgroup CASCADE")


class Migration(migrations.Migration):

    dependencies = [
        ("team", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(name="person", table="team_person"),
                migrations.AlterModelTable(
                    name="accountgroup", table="team_accountgroup"
                ),
                migrations.AlterModelTable(
                    name="skillgroup", table="team_skillgroup"
                ),
                migrations.AlterModelTable(name="account", table="team_account"),
                migrations.AlterModelTable(name="skill", table="team_skill"),
            ],
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
        ),
    ]
