from __future__ import annotations

import json
from datetime import date
from typing import cast
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings

from core import crypto
from core.fields import FernetEncryptedTextField
from core.models import Credential, Network
from core.models.user import UserManager
from core.security_warnings import collect_secrets_rotation_warnings
from core.signals import rotate_session_on_login

User = get_user_model()

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


class SecurityWarningsTests(TestCase):
    @override_settings(
        SECRET_KEY_ROTATED_AT="2020-01-01",
        CREDENTIALS_ENCRYPTION_KEY_ROTATED_AT="2020-01-01",
        SECRETS_ROTATION_MAX_AGE_DAYS=90,
    )
    def test_collect_warnings_for_aged_secret_metadata(self):
        warnings = collect_secrets_rotation_warnings(today=date(2026, 6, 1))
        self.assertTrue(any("SECRET_KEY" in item for item in warnings))
        self.assertTrue(any("CREDENTIALS_ENCRYPTION_KEY" in item for item in warnings))


class SessionRotationTests(TestCase):
    def test_rotate_session_on_login_cycles_session_key(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            email="staff@example.com",
            password="test-password-12",
            is_staff=True,
        )
        from django.contrib.sessions.backends.db import SessionStore

        session = SessionStore()
        session.create()
        old_key = session.session_key

        factory = RequestFactory()
        request = factory.get("/")
        request.session = session

        rotate_session_on_login(sender=None, request=request, user=user)

        self.assertNotEqual(session.session_key, old_key)


class LockoutEmailTests(TestCase):
    @override_settings(
        ADMIN_EMAIL="admin@example.com", DEFAULT_FROM_EMAIL="noreply@test"
    )
    @patch("core.signals.send_mail")
    def test_handle_user_locked_out_sends_admin_email(self, send_mail_mock):
        from core.signals import handle_user_locked_out

        factory = RequestFactory()
        request = factory.post("/login/")
        handle_user_locked_out(
            sender=None,
            request=request,
            username="user@example.com",
            ip_address="203.0.113.10",
        )
        send_mail_mock.assert_called_once()
        self.assertIn("user@example.com", send_mail_mock.call_args.kwargs["message"])


class DevCanonicalHostMiddlewareTests(TestCase):
    def test_redirects_zero_host_to_localhost(self):
        response = self.client.get("/", HTTP_HOST="0.0.0.0:8888")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://localhost:8888/")

    def test_redirects_loopback_ip_to_localhost(self):
        response = self.client.get("/about/", HTTP_HOST="127.0.0.1:8888")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://localhost:8888/about/")

    def test_keeps_localhost_unchanged(self):
        response = self.client.get("/", HTTP_HOST="localhost:8888")
        self.assertEqual(response.status_code, 200)

    def test_api_paths_skip_redirect(self):
        response = self.client.post(
            "/api/editor/v1/auth/logout/",
            HTTP_HOST="127.0.0.1:8888",
        )
        self.assertNotEqual(response.status_code, 302)

    @override_settings(IS_PRODUCTION=True)
    def test_skips_redirect_in_production(self):
        response = self.client.get("/", HTTP_HOST="0.0.0.0:8888")
        self.assertEqual(response.status_code, 200)


class AdminSessionKeepaliveTests(TestCase):
    def setUp(self):
        self.staff = cast(UserManager, User.objects).create_user(
            email="staff@example.com",
            password="secret12345",
            is_staff=True,
        )

    @override_settings(ADMIN_URL="mellon")
    def test_keepalive_requires_staff(self):
        response = self.client.get("/mellon/session-keepalive/")
        self.assertEqual(response.status_code, 302)

    @override_settings(ADMIN_URL="mellon")
    def test_keepalive_refreshes_staff_session(self):
        self.client.force_login(self.staff)
        response = self.client.get("/mellon/session-keepalive/")
        self.assertEqual(response.status_code, 204)
