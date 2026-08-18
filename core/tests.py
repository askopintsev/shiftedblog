from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import cast
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core import crypto
from core.fields import FernetEncryptedTextField
from core.models import Credential, Network
from core.models.user import User as CoreUser
from core.models.user import UserManager
from core.security_warnings import collect_secrets_rotation_warnings
from core.services.site_domain import (
    cookie_parent_domain,
    hostname_from_site_url,
    sync_sites_framework_from_site_url,
)
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


class SiteSettingsTests(TestCase):
    def test_get_site_settings_is_singleton(self):
        from core.models import SiteSettings, get_site_settings

        a = get_site_settings()
        b = get_site_settings()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_context_processor_exposes_site_name(self):
        from core.models import SiteSettings

        SiteSettings.objects.filter(pk=1).update(site_name="Custom Blog")
        from django.core.cache import cache

        cache.clear()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Custom Blog")

    @override_settings(ADMIN_EMAIL="env-admin@example.com")
    def test_effective_email_falls_back_to_env(self):
        from core.models import SiteSettings
        from core.services.site_settings import SiteSettingsService

        SiteSettings.objects.filter(pk=1).update(admin_email="")
        from django.core.cache import cache

        cache.clear()
        cfg = SiteSettingsService.effective_email()
        self.assertEqual(cfg.admin_email, "env-admin@example.com")


class SiteDomainSyncTests(TestCase):
    def test_hostname_and_cookie_parent(self):
        self.assertEqual(
            hostname_from_site_url("https://www.shiftedstuff.space/"),
            "www.shiftedstuff.space",
        )
        self.assertEqual(
            cookie_parent_domain("www.shiftedstuff.space"),
            "shiftedstuff.space",
        )

    @override_settings(SITE_URL="https://www.shiftedstuff.space", SITE_ID=1)
    def test_sync_updates_contrib_sites(self):
        from django.contrib.sites.models import Site

        site = sync_sites_framework_from_site_url()
        self.assertEqual(site.pk, 1)
        self.assertEqual(site.domain, "www.shiftedstuff.space")
        stored = Site.objects.get(pk=1)
        self.assertEqual(stored.domain, "www.shiftedstuff.space")


class RestoreDbCommandTests(TestCase):
    @override_settings(SITE_URL="https://www.example.com")
    @patch.dict(
        "os.environ",
        {
            "DB_NAME": "shiftedblog",
            "DB_USER": "shiftedblog",
            "DB_PASS": "secret",
            "DB_HOST": "db",
        },
        clear=False,
    )
    def test_refuses_non_empty_database_without_force(self):
        dump = Path("/tmp/shiftedblog_pg_dump_test.sql.gz")
        with (
            patch(
                "core.management.commands.restore_db.Command._public_table_count",
                return_value=12,
            ),
            patch(
                "core.management.commands.restore_db.Path.is_file", return_value=True
            ),
            self.assertRaises(CommandError) as ctx,
        ):
            call_command("restore_db", dump=str(dump), skip_media=True)
        self.assertIn("not empty", str(ctx.exception))


def _load_render_nginx_conf():
    path = Path(__file__).resolve().parents[1] / "scripts" / "render_nginx_conf.py"
    spec = importlib.util.spec_from_file_location("render_nginx_conf", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NginxRedirectRenderTests(TestCase):
    def test_legacy_and_apex_redirect_to_www_site_url(self):
        render = _load_render_nginx_conf()
        template = (
            "HTTP:__HTTP_SERVER_NAMES__\n"
            "HTTPS:__HTTPS_SERVER_NAMES__\n"
            "EDITOR:__EDITOR_SERVER_NAMES__\n"
            "BLOCKS:__REDIRECT_HTTPS_BLOCKS__\n"
        )
        text = render.render(
            {
                "DOMAIN": "shiftedstuff.space",
                "SITE_URL": "https://www.shiftedstuff.space",
                "EDITOR_DOMAIN": "editor.shiftedstuff.space",
                "REDIRECT_FROM_DOMAINS": "shiftedstuff.ru,www.shiftedstuff.ru",
                "REDIRECT_FROM_EDITOR_DOMAINS": "editor.shiftedstuff.ru",
            },
            template,
        )
        self.assertIn("www.shiftedstuff.space", text)
        self.assertIn("shiftedstuff.ru", text)
        https_line = next(
            line for line in text.splitlines() if line.startswith("HTTPS:")
        )
        self.assertIn("www.shiftedstuff.space", https_line)
        self.assertNotIn("shiftedstuff.ru", https_line)
        self.assertIn("return 301 https://www.shiftedstuff.space$request_uri", text)
        self.assertIn("return 301 https://editor.shiftedstuff.space$request_uri", text)
        blocks = text.split("BLOCKS:", 1)[1]
        self.assertIn("shiftedstuff.space", blocks)


@override_settings(ADMIN_URL="mellon")
class UserAdminTests(TestCase):
    def setUp(self):
        self.admin = cast(UserManager, CoreUser.objects).create_superuser(
            email="admin@example.com",
            password="secret",
        )
        self.client = Client()

    def test_user_change_view_loads(self):
        self.client.force_login(self.admin)
        url = reverse("admin:core_user_change", args=[self.admin.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
