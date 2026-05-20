from __future__ import annotations

import json

from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from core import crypto
from core.fields import FernetEncryptedTextField
from core.models import Credential, Network

_FERNET_TEST_KEY = Fernet.generate_key().decode("ascii")


@override_settings(CREDENTIALS_ENCRYPTION_KEY=_FERNET_TEST_KEY)
class CredentialStorageTests(TestCase):
    def setUp(self):
        self.net = Network.objects.create(slug="telegram", name="Telegram")

    def test_plaintext_json_in_db_is_readable_and_reencrypted_on_save(self):
        plain = json.dumps({"bot_token": "x", "channel_name": "ch"})
        cred = Credential.objects.create(
            network=self.net,
            label="legacy",
        )
        Credential.objects.filter(pk=cred.pk).update(encrypted_payload=plain)
        cred.refresh_from_db()
        self.assertEqual(cred.get_secrets_dict()["bot_token"], "x")
        cred.save()
        stored = Credential.get_stored_payload_raw(cred.pk)
        self.assertTrue(crypto.looks_like_fernet_token(stored))
        cred.refresh_from_db()
        self.assertEqual(cred.get_secrets_dict()["channel_name"], "ch")

    def test_field_decrypts_fernet_roundtrip(self):
        field = FernetEncryptedTextField()
        token = crypto.encrypt_text('{"a": 1}')
        self.assertEqual(
            field.from_db_value(token, None, None),
            '{"a": 1}',
        )

    def test_field_rejects_corrupt_stored_value(self):
        field = FernetEncryptedTextField()
        with self.assertRaises(ValidationError):
            field.from_db_value("not-json-and-not-fernet", None, None)
