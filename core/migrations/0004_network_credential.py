# Generated manually for multi-channel posting.

import django.db.models.deletion
from django.db import migrations, models

import core.fields


def seed_networks(apps, schema_editor):
    Network = apps.get_model("core", "Network")
    for slug, name in (
        ("site", "Site"),
        ("telegram", "Telegram"),
    ):
        Network.objects.get_or_create(slug=slug, defaults={"name": name})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_user_groups"),
    ]

    operations = [
        migrations.CreateModel(
            name="Network",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(help_text="Stable id, e.g. site, telegram.", max_length=64, unique=True, db_index=True)),
                ("name", models.CharField(max_length=120)),
            ],
            options={
                "db_table": "core_network",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Credential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, default="", help_text='Optional, e.g. "production".', max_length=120)),
                (
                    "encrypted_payload",
                    core.fields.FernetEncryptedTextField(
                        blank=True,
                        default="",
                        help_text='Encrypted JSON object, e.g. {"bot_token": "…", "chat_id": "…"}.',
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "network",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credentials",
                        to="core.network",
                    ),
                ),
            ],
            options={
                "db_table": "core_credential",
                "ordering": ["network__slug", "label"],
            },
        ),
        migrations.AddConstraint(
            model_name="credential",
            constraint=models.UniqueConstraint(
                fields=("network", "label"),
                name="core_credential_network_label_uniq",
            ),
        ),
        migrations.RunPython(seed_networks, noop_reverse),
    ]
