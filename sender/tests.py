"""Tests for the sender subsystem."""

from __future__ import annotations

from typing import cast
from unittest import mock

from cryptography.fernet import Fernet
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import SitePublication
from core.models import NETWORK_SLUG_SITE, NETWORK_SLUG_TELEGRAM, Credential, Network
from core.models.user import User, UserManager
from editor.models import Category, Post, PostGalleryImage
from sender.models import PostLink
from sender.services.post_sender import run_publish_job
from sender.services.telegram_channel import (
    channel_has_subscription,
    channel_owner_has_premium,
)
from sender.services.telegram_format import (
    adjust_split_index_for_telegram_html,
    balance_telegram_html,
    build_formatted_message,
    find_telegram_html_split_index,
    html_body_to_telegram_html,
)
from sender.services.telegram_plan import (
    CONTINUATION_PREFIX,
    MAX_CAPTION_LEN,
    MAX_MESSAGE_LEN,
    build_preview_payload,
    build_preview_send_cards,
    build_telegram_plan,
    caption_for_step,
)
from sender.services.telegram_publisher import resolve_telegram_plan
from sender.services.url_helpers import public_post_url

_FERNET_TEST_KEY = Fernet.generate_key().decode("ascii")


class TelegramFormatTests(TestCase):
    def test_title_body_tags_template(self):
        post = Post(title="Title", body="<p>Hello <strong>world</strong></p>")
        post.save()
        post.tags.add("news", "django")
        text = build_formatted_message(post)
        self.assertTrue(text.startswith("<b>Title</b>\n\n"))
        self.assertIn("<b>world</b>", text)
        self.assertIn("#news", text)
        self.assertIn("#django", text)

    def test_h3_gets_blank_line_and_bold(self):
        html = "<h3>Section</h3><p>After</p>"
        out = html_body_to_telegram_html(html)
        self.assertIn("<b>Section</b>", out)
        self.assertNotIn("<b><b>", out)

    def test_h3_with_inner_strong_is_single_bold(self):
        html = "<h3><strong>Title</strong></h3><p><strong>1906</strong> — year</p>"
        out = html_body_to_telegram_html(html)
        self.assertNotIn("<b><b>", out)
        self.assertIn("<b>Title</b>", out)
        self.assertIn("<b>1906</b>", out)

    def test_paragraphs_keep_line_breaks(self):
        html = "<p>First line</p><p>Second line</p>"
        out = html_body_to_telegram_html(html)
        self.assertIn("First line\n\nSecond line", out)

    def test_br_keeps_single_line_break_inside_paragraph(self):
        html = "<p>Line one<br>Line two</p>"
        out = html_body_to_telegram_html(html)
        self.assertIn("Line one\nLine two", out)

    def test_ckeditor_span_bold_converts_to_telegram_b(self):
        html = '<p><span style="font-weight:bold">Bold</span> plain</p>'
        out = html_body_to_telegram_html(html)
        self.assertIn("<b>Bold</b>", out)

    def test_whitespace_only_strong_tag_keeps_word_gap(self):
        html = '<p>А первой<strong> </strong>песней, "официально"</p>'
        out = html_body_to_telegram_html(html)
        self.assertIn("первой песней", out)
        self.assertNotIn("первойпесней", out)

    def test_trailing_space_inside_strong_before_plain_word(self):
        html = "<p>1 июня запущен сайт <strong>Napster. </strong>Его часто</p>"
        out = html_body_to_telegram_html(html)
        self.assertNotIn("Napster.Его", out)
        self.assertRegex(out, r"Napster\.\s*</b>Его")

    def test_balance_closes_unclosed_tags(self):
        from sender.services.telegram_format import balance_telegram_html

        self.assertEqual(balance_telegram_html("<b>Title"), "<b>Title</b>")

    def test_split_moves_before_styled_block_when_cut_inside_style(self):
        bold_start = "Intro. "
        bold_body = "<b>" + ("styled word. " * 120) + "</b>"
        text = bold_start + bold_body + " tail."
        naive_split = len(bold_start) + 50
        self.assertLess(naive_split, text.index("</b>"))
        adjusted = adjust_split_index_for_telegram_html(text, naive_split)
        self.assertEqual(adjusted, text.index("<b>"))
        self.assertNotIn("<b>", text[:adjusted])

    def test_find_split_index_keeps_bold_block_in_one_chunk(self):
        prefix = "A" * 3800 + ". "
        bold = "<b>" + ("Bold sentence. " * 40) + "</b>"
        text = prefix + bold
        split_at = find_telegram_html_split_index(text, 4096)
        first = balance_telegram_html(text[:split_at].rstrip())
        self.assertNotIn("<b>", first)
        self.assertTrue(text[split_at:].lstrip().startswith("<b>"))

    def test_series_split_does_not_break_bold_paragraph(self):
        prefix = "word " * 2000
        bold = "<b>" + "styled " * 500 + "</b>"
        suffix = " word" * 2000
        body = f"<p>{prefix}{bold}{suffix}</p>"
        post = Post(title="", body=body)
        plan = build_telegram_plan(post, has_subscription=False)
        self.assertGreater(len(plan.steps), 1)
        for step in plan.steps:
            if "<b>" in step.text or "</b>" in step.text:
                self.assertIn("<b>", step.text)
                self.assertIn("</b>", step.text)
        combined = "".join(
            step.text.removeprefix(f"{CONTINUATION_PREFIX}\n\n")
            for step in plan.steps
        )
        self.assertIn("<b>", combined)
        self.assertIn("</b>", combined)

    def test_code_block_split_moves_to_pre_start(self):
        text = "Start. <pre>" + ("code line\n" * 80) + "</pre> end."
        split_at = find_telegram_html_split_index(text, 120)
        self.assertEqual(split_at, text.index("<pre>"))

    def test_code_block_uses_pre_only(self):
        html = '<pre><code class="language-python">x = 1</code></pre>'
        out = html_body_to_telegram_html(html)
        self.assertIn("<pre>x = 1</pre>", out)
        self.assertNotIn("<code>", out)

    def test_gallery_placeholder_removed_from_body(self):
        html = "<p>Before [gallery:1] after</p>"
        out = html_body_to_telegram_html(html)
        self.assertIn("Before", out)
        self.assertIn("after", out)
        self.assertNotIn("[gallery", out)

    def test_nbsp_and_zwsp_normalized_in_body(self):
        html = "<p>word&nbsp;next</p><p>zero\u200bwidth</p>"
        out = html_body_to_telegram_html(html)
        self.assertNotIn("&nbsp;", out)
        self.assertNotIn("\xa0", out)
        self.assertNotIn("\u200b", out)
        self.assertIn("word next", out)
        self.assertIn("zerowidth", out)

    def test_continuation_prefix_on_second_chunk(self):
        post = Post(title="", body=f"<p>{'word ' * 3000}</p>")
        plan = build_telegram_plan(post, has_subscription=False)
        self.assertGreater(len(plan.steps), 1)
        self.assertTrue(plan.steps[1].text.startswith(f"{CONTINUATION_PREFIX}\n\n"))

    def test_series_tags_on_first_and_last_parts(self):
        post = Post(title="Tagged", body=f"<p>{'word ' * 3000}</p>")
        post.save()
        post.tags.add("news", "django")
        plan = build_telegram_plan(post, has_subscription=False)
        self.assertGreater(len(plan.steps), 1)
        self.assertIn("#news", plan.steps[0].text)
        self.assertIn("#django", plan.steps[0].text)
        self.assertIn("#news", plan.steps[-1].text)
        self.assertIn("#django", plan.steps[-1].text)
        self.assertLessEqual(len(plan.steps[0].text), MAX_MESSAGE_LEN)
        self.assertLessEqual(len(plan.steps[-1].text), MAX_MESSAGE_LEN)
        if len(plan.steps) > 2:
            for step in plan.steps[1:-1]:
                self.assertNotIn("#news", step.text)
                self.assertNotIn("#django", step.text)


class TelegramPreviewSendCardsTests(TestCase):
    def test_subscription_splits_cover_and_message_cards(self):
        post = Post(
            title="T",
            body="<p>Short body</p>",
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
        )
        plan = build_telegram_plan(post, has_subscription=True)
        cards = build_preview_send_cards(plan)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["kind"], "photo")
        self.assertFalse(cards[0]["has_text"])
        self.assertEqual(cards[1]["kind"], "message")
        self.assertEqual(cards[1]["max_chars"], MAX_MESSAGE_LEN)

    def test_long_text_with_cover_splits_caption_and_message(self):
        sentences = "First sentence. " * 80 + "Last overflow sentence."
        post = Post(
            title="Long",
            body=f"<p>{sentences}</p>",
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
        )
        plan = build_telegram_plan(post, has_subscription=False)
        self.assertGreater(len(plan.steps), 1)
        self.assertLessEqual(len(plan.steps[0].text), MAX_CAPTION_LEN)
        self.assertTrue(plan.steps[0].text.rstrip().endswith("."))
        cards = build_preview_send_cards(plan)
        self.assertEqual(cards[0]["kind"], "photo")
        self.assertTrue(cards[0]["has_text"])
        self.assertIn("sentence", cards[0]["limit_note"])
        self.assertEqual(cards[1]["kind"], "message")
        self.assertTrue(cards[1]["text"].startswith(f"{CONTINUATION_PREFIX}\n\n"))

    def test_short_text_with_cover_uses_caption_card(self):
        post = Post(
            title="Cap",
            body="<p>Short</p>",
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
        )
        plan = build_telegram_plan(post, has_subscription=False)
        cards = build_preview_send_cards(plan)
        self.assertEqual(cards[0]["kind"], "photo")
        self.assertTrue(cards[0]["has_text"])
        self.assertEqual(cards[0]["max_chars"], MAX_CAPTION_LEN)
        self.assertEqual(caption_for_step(plan.steps[0], has_subscription=False), cards[0]["text"])
        self.assertEqual(len(cards), 1)

    def test_series_preview_numbers_all_sends(self):
        post = Post(title="", body=f"<p>{'word ' * 3000}</p>")
        plan = build_telegram_plan(post, has_subscription=False)
        payload = build_preview_payload(plan)
        self.assertTrue(payload["is_series"])
        self.assertGreater(payload["step_count"], 1)
        self.assertEqual(payload["send_count"], len(payload["cards"]))
        self.assertEqual(payload["cards"][0]["send_index"], 1)
        self.assertEqual(payload["cards"][-1]["send_total"], payload["send_count"])


class TelegramChannelPlanTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_channel_has_subscription_from_secrets(self):
        self.assertTrue(
            channel_has_subscription({"channel_subscription": True}),
        )
        self.assertFalse(
            channel_has_subscription({"channel_subscription": False}),
        )

    def test_channel_has_subscription_detects_owner_premium(self):
        api_resp = {
            "ok": True,
            "result": [
                {
                    "status": "creator",
                    "user": {"id": 1, "is_premium": True},
                },
            ],
        }
        with mock.patch(
            "sender.services.telegram_channel._api_get",
            return_value=api_resp,
        ):
            self.assertTrue(
                channel_has_subscription(
                    {},
                    token="tok",
                    chat_id="@chan-premium",
                ),
            )

    def test_channel_owner_has_premium_false(self):
        api_resp = {
            "ok": True,
            "result": [
                {
                    "status": "creator",
                    "user": {"id": 2, "is_premium": False},
                },
            ],
        }
        with mock.patch(
            "sender.services.telegram_channel._api_get",
            return_value=api_resp,
        ):
            self.assertFalse(channel_owner_has_premium("tok", "@chan-no-premium"))

    def test_explicit_false_skips_api(self):
        with mock.patch("sender.services.telegram_channel._api_get") as m:
            self.assertFalse(
                channel_has_subscription(
                    {"channel_subscription": False},
                    token="tok",
                    chat_id="@chan",
                ),
            )
            m.assert_not_called()

    def test_subscription_splits_cover_and_text(self):
        post = Post(
            title="T",
            body="<p>Short</p>",
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
        )
        plan = build_telegram_plan(post, has_subscription=True)
        self.assertEqual(len(plan.steps), 1)
        self.assertTrue(plan.has_subscription)
        from sender.services.telegram_plan import caption_for_step

        self.assertIsNone(
            caption_for_step(plan.steps[0], has_subscription=True),
        )

    def test_preview_and_publish_share_same_plan(self):
        post = Post(
            title="Same",
            body="<p>Hello <strong>world</strong></p>",
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
        )
        post.save()
        secrets = {"channel_subscription": False}
        with mock.patch(
            "sender.services.telegram_channel._api_get",
            return_value={"ok": True, "result": []},
        ):
            preview_plan = resolve_telegram_plan(post, secrets)
            publish_plan = resolve_telegram_plan(post, secrets)
        self.assertEqual(
            preview_plan.steps[0].text,
            publish_plan.steps[0].text,
        )
        self.assertIn("<b>world</b>", preview_plan.steps[0].text)


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
        self.assertGreaterEqual(m.call_count, 1)
        first = m.call_args_list[0]
        chat_id = (first.kwargs.get("data") or first.kwargs.get("json") or {}).get(
            "chat_id",
        )
        self.assertEqual(chat_id, "@chan")
        self.assertIn("sendPhoto", first.args[0])
        tg_net = Network.objects.get(slug=NETWORK_SLUG_TELEGRAM)
        pl = PostLink.objects.get(post=self.post, network=tg_net)
        self.assertIn("t.me", pl.url)

    def test_publish_sends_preview_formatted_text(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"username": "chan", "id": -100},
            },
        }
        mock_resp.text = "{}"
        plan = resolve_telegram_plan(self.post)
        preview_text = plan.steps[0].text
        with (
            mock.patch(
                "sender.services.telegram_publisher._api_post_multipart",
            ) as photo_api,
            mock.patch(
                "sender.services.telegram_publisher._api_post_json",
            ) as msg_api,
        ):
            photo_api.return_value = (mock_resp.json.return_value, mock_resp)
            msg_api.return_value = (mock_resp.json.return_value, mock_resp)
            from sender.services.telegram_publisher import publish_to_telegram

            publish_to_telegram(self.post)
        photo_fields = photo_api.call_args[0][2]
        self.assertEqual(photo_fields["parse_mode"], (None, "HTML"))
        self.assertEqual(photo_fields["caption"][1], preview_text)
        msg_api.assert_not_called()

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

    def test_publish_workflow_telegram_preview(self):
        author = cast(UserManager, User.objects).create_user(
            email="preview@example.com",
            password="x",
        )
        cat = Category.objects.create(name="Cat")
        post = Post.objects.create(
            title="Preview",
            slug="preview-tg",
            author=author,
            body="<p>Preview body</p>",
            status="ready_to_publish",
            category=cat,
        )
        self.client.force_login(self.admin)
        url = reverse("sender_publish_workflow")
        rsp = self.client.get(
            url,
            {"post_id": post.pk, "preview_telegram": "1"},
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Expected Telegram sends")
        self.assertContains(rsp, 'class="telegram-preview-card"')
        self.assertContains(rsp, 'class="telegram-preview-text"')
        self.assertContains(rsp, "<b>Preview</b>")
        self.assertNotContains(rsp, "<pre")
        self.assertContains(rsp, 'id="telegram-preview"')
        post.refresh_from_db()
        self.assertEqual(post.status, "ready_to_publish")

    def test_publish_workflow_telegram_preview_shows_image_thumbnails(self):
        author = cast(UserManager, User.objects).create_user(
            email="preview-img@example.com",
            password="x",
        )
        cat = Category.objects.create(name="Cat")
        post = Post.objects.create(
            title="Preview images",
            slug="preview-tg-images",
            author=author,
            body="<p>Preview body</p>",
            status="ready_to_publish",
            category=cat,
            cover_image=SimpleUploadedFile(
                "cover.jpg",
                b"cover-bytes",
                content_type="image/jpeg",
            ),
        )
        PostGalleryImage.objects.create(
            post=post,
            gallery_key=1,
            image=SimpleUploadedFile(
                "gallery.jpg",
                b"gallery-bytes",
                content_type="image/jpeg",
            ),
        )
        self.client.force_login(self.admin)
        url = reverse("sender_publish_workflow")
        rsp = self.client.get(
            url,
            {"post_id": post.pk, "preview_telegram": "1"},
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, 'class="telegram-preview-cover"')
        self.assertContains(rsp, 'class="telegram-preview-thumb"')
        self.assertContains(rsp, "Send 1/")
        self.assertContains(rsp, post.cover_image.url)
        self.assertContains(rsp, post.gallery_images.first().image.url)
        author = cast(UserManager, User.objects).create_user(
            email="nopub@example.com",
            password="x",
        )
        cat = Category.objects.create(name="Cat")
        post = Post.objects.create(
            title="No publish on preview",
            slug="no-pub-preview",
            author=author,
            body="<p>Body</p>",
            status="ready_to_publish",
            category=cat,
        )
        self.client.force_login(self.admin)
        url = reverse("sender_publish_workflow")
        with mock.patch("sender.admin_views.run_publish_job") as publish_job:
            rsp = self.client.get(
                url,
                {"post_id": post.pk, "preview_telegram": "1"},
            )
        self.assertEqual(rsp.status_code, 200)
        publish_job.assert_not_called()

    def test_publish_workflow_preview_requires_post_selection(self):
        self.client.force_login(self.admin)
        url = reverse("sender_publish_workflow")
        rsp = self.client.get(url, {"preview_telegram": "1"})
        self.assertEqual(rsp.status_code, 200)
        self.assertNotContains(rsp, "Expected Telegram messages")
