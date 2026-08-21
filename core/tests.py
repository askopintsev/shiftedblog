from __future__ import annotations

import importlib.util
import io
import json
import tempfile
from datetime import date
from pathlib import Path
from typing import cast
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

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
        self.net, _ = Network.objects.get_or_create(
            slug="telegram", defaults={"name": "Telegram"}
        )

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
        dump = Path(tempfile.gettempdir()) / "shiftedblog_pg_dump_test.sql.gz"
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
    _STUB_TEMPLATE = (
        "HTTP:__HTTP_SERVER_NAMES__\n"
        "MAIN:__MAIN_HTTPS_SERVER__\n"
        "EDITOR:__EDITOR_SERVER_NAMES__\n"
        "EXTRA:__EDITOR_EXTRA_LOCATIONS__\n"
        "BLOCKS:__REDIRECT_HTTPS_BLOCKS__\n"
    )

    def _render_root(self):
        return Path(__file__).resolve().parents[1]

    def test_legacy_and_apex_redirect_to_www_site_url(self):
        render = _load_render_nginx_conf()
        text = render.render(
            {
                "DOMAIN": "shiftedstuff.space",
                "SITE_URL": "https://www.shiftedstuff.space",
                "EDITOR_DOMAIN": "editor.shiftedstuff.space",
                "REDIRECT_FROM_DOMAINS": "shiftedstuff.ru,www.shiftedstuff.ru",
                "REDIRECT_FROM_EDITOR_DOMAINS": "editor.shiftedstuff.ru",
            },
            self._STUB_TEMPLATE,
            template_root=self._render_root(),
        )
        self.assertIn("www.shiftedstuff.space", text)
        self.assertIn("shiftedstuff.ru", text)
        main_block = text.split("MAIN:", 1)[1].split("EDITOR:", 1)[0]
        self.assertIn("www.shiftedstuff.space", main_block)
        self.assertNotIn("shiftedstuff.ru", main_block)
        self.assertIn("return 301 https://www.shiftedstuff.space$request_uri", text)
        self.assertIn("return 301 https://editor.shiftedstuff.space$request_uri", text)
        blocks = text.split("BLOCKS:", 1)[1]
        self.assertIn("shiftedstuff.space", blocks)

    def test_private_mode_omits_main_https_and_adds_staff_paths(self):
        render = _load_render_nginx_conf()
        text = render.render(
            {
                "PUBLIC_SITE_ENABLED": "false",
                "DOMAIN": "example.com",
                "SITE_URL": "https://editor.example.com",
                "EDITOR_DOMAIN": "editor.example.com",
                "ADMIN_URL": "abc123def",
            },
            self._STUB_TEMPLATE,
            template_root=self._render_root(),
        )
        self.assertIn("HTTP:editor.example.com", text)
        self.assertNotIn("MAIN:    # HTTPS server", text)
        main_block = text.split("MAIN:", 1)[1].split("EDITOR:", 1)[0].strip()
        self.assertEqual(main_block, "")
        extra = text.split("EXTRA:", 1)[1].split("BLOCKS:", 1)[0]
        self.assertIn("/lenta/", extra)
        self.assertIn("/abc123def/", extra)
        self.assertIn("/static/", extra)

    def test_private_mode_includes_server_ip_on_editor_vhost(self):
        render = _load_render_nginx_conf()
        text = render.render(
            {
                "PUBLIC_SITE_ENABLED": "false",
                "DOMAIN": "shiftedblog.local",
                "SITE_URL": "https://editor.shiftedblog.local",
                "EDITOR_DOMAIN": "editor.shiftedblog.local",
                "SERVER_IP": "203.0.113.10",
                "ADMIN_URL": "abc123def",
            },
            self._STUB_TEMPLATE,
            template_root=self._render_root(),
        )
        editor_block = text.split("EDITOR:", 1)[1].split("EXTRA:", 1)[0]
        self.assertIn("editor.shiftedblog.local", editor_block)
        self.assertIn("203.0.113.10", editor_block)


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


class CorePublicErrorAndRobotsTests(TestCase):
    def test_robots_txt_disallows_admin(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Disallow: /mellon/", response.content.decode())
        self.assertIn("Sitemap:", response.content.decode())

    def test_unknown_path_renders_404_template(self):
        response = self.client.get("/this-path-does-not-exist-coverage/")
        self.assertEqual(response.status_code, 404)

    def test_error_handlers_render(self):
        factory = RequestFactory()
        request = factory.get("/")
        from core.views import (
            custom_bad_request_view,
            custom_error_view,
            custom_page_not_found_view,
            custom_permission_denied_view,
        )

        self.assertEqual(
            custom_page_not_found_view(request, Exception()).status_code, 404
        )
        self.assertEqual(custom_permission_denied_view(request).status_code, 200)
        self.assertEqual(custom_bad_request_view(request).status_code, 200)
        self.assertEqual(custom_error_view(request).status_code, 200)

    def test_robots_txt_falls_back_to_request_host(self):
        response = self.client.get("/robots.txt")
        self.assertIn("Sitemap:", response.content.decode())

    def test_custom_image_upload_rejects_bad_type_and_empty_request(self):
        staff = cast(UserManager, User.objects).create_user(
            email="upload@example.com",
            password="secret12345",
            is_staff=True,
        )
        self.client.force_login(staff)
        empty = self.client.post("/custom-image-upload/")
        self.assertEqual(empty.status_code, 400)
        bad = self.client.post(
            "/custom-image-upload/",
            {
                "upload": SimpleUploadedFile(
                    "notes.txt",
                    b"hi",
                    content_type="text/plain",
                )
            },
        )
        self.assertEqual(bad.status_code, 400)

    def test_custom_image_upload_accepts_png(self):
        staff = cast(UserManager, User.objects).create_user(
            email="upload-ok@example.com",
            password="secret12345",
            is_staff=True,
        )
        self.client.force_login(staff)
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), color="red").save(buf, format="PNG")
        uploaded = SimpleUploadedFile(
            "shot.png",
            buf.getvalue(),
            content_type="image/png",
        )
        response = self.client.post("/custom-image-upload/", {"upload": uploaded})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["uploaded"], 1)


@override_settings(CREDENTIALS_ENCRYPTION_KEY=_FERNET_TEST_KEY)
class CryptoHelperTests(TestCase):
    def test_empty_and_invalid_payloads(self):
        self.assertEqual(crypto.decrypt_text(""), "")
        self.assertEqual(crypto.encrypt_text(""), "")
        self.assertEqual(crypto.payload_plaintext_from_stored(""), "")
        self.assertEqual(crypto.payload_plaintext_from_stored("not-encrypted"), "")
        self.assertEqual(
            crypto.payload_plaintext_from_stored('{"bot_token": "x"}'),
            '{"bot_token": "x"}',
        )
        with self.assertRaises(ValueError):
            other = Fernet.generate_key()
            token = Fernet(other).encrypt(b"secret").decode("ascii")
            crypto.decrypt_bytes(token)

    def test_invalid_fernet_key_raises(self):
        with (
            override_settings(CREDENTIALS_ENCRYPTION_KEY="not-a-key"),
            self.assertRaises(ImproperlyConfigured),
        ):
            crypto.get_fernet()
        with (
            override_settings(CREDENTIALS_ENCRYPTION_KEY=""),
            self.assertRaises(ImproperlyConfigured),
        ):
            crypto.get_fernet()

    def test_encrypted_field_empty_and_plaintext_prep(self):
        field = FernetEncryptedTextField()
        self.assertEqual(field.from_db_value("", None, None), "")
        self.assertEqual(field.to_python(None), "")
        self.assertEqual(field.to_python(12), "12")
        self.assertEqual(field.get_prep_value(""), "")
        stored = field.get_prep_value('{"a": 1}')
        self.assertTrue(crypto.looks_like_fernet_token(stored))
