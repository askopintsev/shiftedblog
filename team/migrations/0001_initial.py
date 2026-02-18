# Generated manually for moving blog Person, Account, Skill models to team (tables unchanged)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="AccountGroup",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_accountgroup"},
                ),
                migrations.CreateModel(
                    name="Person",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("avatar", models.ImageField(upload_to="img/template/")),
                        ("name", models.CharField(max_length=250)),
                        ("greeting", models.TextField()),
                        ("biography", models.TextField()),
                    ],
                    options={"db_table": "blog_person"},
                ),
                migrations.CreateModel(
                    name="SkillGroup",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                    ],
                    options={"db_table": "blog_skillgroup"},
                ),
                migrations.CreateModel(
                    name="Account",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                        ("url", models.CharField(max_length=250)),
                        ("icon", models.FileField(upload_to="img/template/")),
                        ("group", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="team.accountgroup")),
                        ("person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="team.person")),
                    ],
                    options={"db_table": "blog_account"},
                ),
                migrations.CreateModel(
                    name="Skill",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=250)),
                        ("rating", models.IntegerField(default=0)),
                        ("group", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="team.skillgroup")),
                        ("person", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="team.person")),
                    ],
                    options={"db_table": "blog_skill"},
                ),
            ],
            database_operations=[],
        ),
    ]
