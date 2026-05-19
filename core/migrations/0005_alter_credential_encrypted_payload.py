# Credential help_text: document channel_name for Telegram.

from django.db import migrations

import core.fields


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_network_credential"),
    ]

    operations = [
        migrations.AlterField(
            model_name="credential",
            name="encrypted_payload",
            field=core.fields.FernetEncryptedTextField(
                blank=True,
                default="",
                help_text=(
                    "Encrypted JSON, e.g. "
                    '{"bot_token": "…", "channel_name": "mychannel"} '
                    '(optional "chat_id" for numeric targets).'
                ),
            ),
        ),
    ]
