"""Tests for the sender subsystem."""

from __future__ import annotations

from typing import cast
from unittest import mock

from cryptography.fernet import Fernet
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import SitePublication
from core.models import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM, Credential, Network
from core.models.user import User, UserManager
from editor.models import Category, Post
from sender.models import PostLink
from sender.services.post_sender import run_publish_job
from sender.services.url_helpers import public_post_url

_FERNET_TEST_KEY = Fernet.generate_key().decode("ascii")


class PublicUrlTests(TestCase):
    @override_settings(SITE_URL="https://example.org")
    def test_public_post_url_joins_site_and_detail_path(self):
        p = Post(title="T", slug="my-slug")
        u = public_post_url(p)
        self.assertIn("example.org", u)
        self.assertIn("my-slug", u)


@override_settings(
    SITE_URL="https://example.org",
    CREDENTIALS_ENCRYPTION_KEY=_FERNET_TEST_KEY,
)
class SitePublishJobTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="sender-test@example.com",
            password="x",
        )
        self.cat = Category.objects.create(name="Cat")
        self.post = Post.objects.create(
            title="Ready",
            slug="ready-sender",
            author=self.author,
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
            body="<p>Hello world</p>",
            status="ready_to_publish",
            category=self.cat,
        )

    def test_site_only_marks_published_and_creates_postlink(self):
        r = run_publish_job(self.post.pk, [NETWORK_SLUG_SITE])
        self.assertTrue(r.all_ok)
        self.assertTrue(r.status_updated)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, "published")
        site_net = Network.objects.get(slug=NETWORK_SLUG_SITE)
        link = PostLink.objects.get(post=self.post, network=site_net)
        self.assertIn("ready-sender", link.url)
        self.assertTrue(
            SitePublication.objects.filter(post=self.post).exists(),
        )


@override_settings(
    SITE_URL="https://example.org",
    CREDENTIALS_ENCRYPTION_KEY=_FERNET_TEST_KEY,
)
class TelegramPublishJobTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="tg-test@example.com",
            password="x",
        )
        self.cat = Category.objects.create(name="Cat")
        self.post = Post.objects.create(
            title="TG",
            slug="tg-ready",
            author=self.author,
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
            body="<p>Body</p>",
            status="ready_to_publish",
            category=self.cat,
        )
        net = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        cred = Credential(network=net, label="")
        cred.set_secrets_dict({"bot_token": "test-token", "channel_name": "chan"})
        cred.save()

    def test_telegram_success_creates_postlink(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"username": "chan", "id": -100},
            },
        }
        mock_resp.text = "{}"
        with mock.patch("sender.services.telegram_publisher.requests.post") as m:
            m.return_value = mock_resp
            r = run_publish_job(
                self.post.pk,
                [NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM],
            )
        self.assertTrue(r.all_ok)
        m.assert_called_once()
        _args, kwargs = m.call_args
        self.assertEqual(kwargs.get("json", {}).get("chat_id"), "@chan")
        tg_net = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        pl = PostLink.objects.get(post=self.post, network=tg_net)
        self.assertIn("t.me", pl.url)

    def test_telegram_numeric_chat_id_unchanged(self):
        net = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        cred = Credential.objects.get(network=net)
        cred.set_secrets_dict({"bot_token": "test-token", "chat_id": "-100555"})
        cred.save()
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 1,
                "chat": {"username": "x", "id": -100},
            },
        }
        mock_resp.text = "{}"
        with mock.patch("sender.services.telegram_publisher.requests.post") as m:
            m.return_value = mock_resp
            r = run_publish_job(self.post.pk, [NETWORK_SLUG_TELEGRAM])
        self.assertTrue(r.all_ok)
        _args, kwargs = m.call_args
        self.assertEqual(kwargs.get("json", {}).get("chat_id"), "-100555")


class PublishWorkflowViewTests(TestCase):
    def setUp(self):
        self.admin = cast(UserManager, User.objects).create_superuser(
            email="adm@example.com",
            password="pw",
        )

    def test_publish_workflow_requires_login(self):
        url = reverse("sender_publish_workflow")
        rsp = self.client.get(url)
        self.assertIn(rsp.status_code, (302, 403))

    def test_publish_workflow_get_ok_for_staff(self):
        self.client.force_login(self.admin)
        url = reverse("sender_publish_workflow")
        rsp = self.client.get(url)
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Multi-channel publish")
