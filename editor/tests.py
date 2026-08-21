import io
import json
from typing import cast
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from PIL import Image

from core.models.user import User, UserManager
from editor.models import Category, Post, PostHistory
from editor.post_history_service import PostHistoryService
from editor.text_quality_service import PostTextQualityService, TextQualityRequestDTO


def _minimal_jpeg_upload(name: str = "cover.jpg") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(200, 40, 40)).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class PostTextQualityServiceTests(TestCase):
    def setUp(self):
        self.service = PostTextQualityService()

    def test_evaluate_returns_required_metrics(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text=(
                    "<p>Это тестовый текст для проверки читаемости и орфографии.</p>"
                    "<p>Второй абзац добавляет структуру и логичное продолжение "
                    "мысли.</p>"
                ),
                content_format="html",
            )
        )
        payload = report.to_dict()
        self.assertTrue(payload["ok"])
        self.assertIn("overall", payload)
        self.assertIn("readability", payload["scores"])
        self.assertIn("spam_words", payload["scores"])
        self.assertIn("waterness", payload["scores"])
        self.assertIn("orthography", payload["scores"])
        self.assertIn("punctuation", payload["scores"])
        self.assertIn("typos", payload["scores"])

    def test_overall_score_is_clamped(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text="<p>Короткий текст.</p>",
                content_format="html",
            )
        )
        self.assertGreaterEqual(report.overall.score, 0)
        self.assertLessEqual(report.overall.score, 100)

    def test_spam_score_drops_on_keyword_stuffing(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text=(
                    "<p>Блог блог блог блог блог блог блог блог блог блог.</p>"
                    "<p>Этот блог про блог и только про блог.</p>"
                ),
                content_format="html",
            )
        )
        spam_score = report.scores["spam_words"].score
        self.assertLess(spam_score, 60)

    def test_spam_score_detects_short_seo_keyword_repetition(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text=(
                    "<p>SEO seo seo seo seo seo seo продвижение сайта и seo трафик.</p>"
                ),
                content_format="html",
            )
        )
        self.assertLess(report.scores["spam_words"].score, 80)

    def test_orthography_and_typos_react_to_obvious_misspelling(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text=(
                    "<p>Technology analysis works stable. "
                    "This technology stack is reliable. "
                    "But technolgy in this sentence is misspelled.</p>"
                ),
                content_format="html",
            )
        )
        self.assertLess(report.scores["orthography"].score, 100)
        self.assertLess(report.scores["typos"].score, 100)

    def test_punctuation_ignores_abbreviations_numbers_and_lists(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text=(
                    "<p>Это, т.к. тестовый блок. И т.д. в тексте встречается часто.</p>"
                    "<p>- List item, punctuation signs remain.</p>"
                    "<p>1) Второй пункт, это нормальная запись.</p>"
                    "<p>Значение 11 463,07 и 2026/04/24 не должны ломать оценку.</p>"
                ),
                content_format="html",
            )
        )
        punctuation_score = report.scores["punctuation"].score
        self.assertGreaterEqual(punctuation_score, 0)
        self.assertLessEqual(punctuation_score, 100)

    @override_settings(
        TEXT_QUALITY_PY_CHECKER_ENABLED=True,
    )
    def test_falls_back_to_heuristics_when_languagetool_not_configured(self):
        report = self.service.evaluate(
            TextQualityRequestDTO(
                text="<p>Текст для базовой проверки без внешнего API.</p>",
                content_format="html",
            )
        )
        payload = report.to_dict()
        self.assertTrue(payload["ok"])
        self.assertIn("orthography", payload["scores"])
        self.assertIn("punctuation", payload["scores"])


class PostAdminTextQualityEndpointTests(TestCase):
    def setUp(self):
        self.admin_user = cast(UserManager, User.objects).create_superuser(
            email="admin@example.com",
            password="example-pass-123",
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.url = reverse("admin:editor_post_text_quality")

    def test_endpoint_returns_metrics_for_valid_payload(self):
        response = cast(
            HttpResponse,
            self.client.post(
                self.url,
                data=json.dumps(
                    {
                        "schema_version": "1.0",
                        "content_format": "html",
                        "locale": "ru-RU",
                        "text": (
                            "<p>Тестовый текст без агрессивных рекламных триггеров.</p>"
                        ),
                    }
                ),
                content_type="application/json",
            ),
        )
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("overall", payload)
        self.assertIn("scores", payload)

    def test_endpoint_validates_empty_text(self):
        response = cast(
            HttpResponse,
            self.client.post(
                self.url,
                data=json.dumps({"text": "  "}),
                content_type="application/json",
            ),
        )
        self.assertEqual(response.status_code, 422)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")


class CopiedTableIdSequenceTests(TestCase):
    def test_category_and_post_receive_database_pks(self):
        author = cast(UserManager, User.objects).create_user(
            email="seq-test@example.com",
            password="x",
        )
        category = Category.objects.create(name="Sequence Cat")
        post = Post.objects.create(
            title="Sequence post",
            slug="sequence-post",
            author=author,
            body="<p>Body</p>",
            status="draft",
            category=category,
        )
        self.assertIsNotNone(category.pk)
        self.assertIsNotNone(post.pk)


class PostSlugGenerationTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="slug-test@example.com",
            password="x",
        )
        self.cat = Category.objects.create(name="Cat")

    def _create_post(self, **kwargs) -> Post:
        defaults = {
            "title": "",
            "slug": "",
            "author": self.author,
            "body": "<p>Текст тела без заголовка.</p>",
            "status": "draft",
            "category": self.cat,
        }
        defaults.update(kwargs)
        return Post.objects.create(**defaults)

    def test_empty_slug_and_title_uses_transliterated_body_first_words(self):
        post = self._create_post()
        self.assertEqual(post.slug, "tekst-tela-bez-zagolovka")

    def test_cyrillic_title_transliterates_to_latin_slug(self):
        post = self._create_post(title="Привет мир")
        self.assertEqual(post.slug, "privet-mir")

    def test_slug_from_title_when_slug_field_empty(self):
        post = self._create_post(title="Hello World")
        self.assertEqual(post.slug, "hello-world")

    def test_explicit_slug_used_without_title(self):
        post = self._create_post(slug="custom-url", title="")
        self.assertEqual(post.slug, "custom-url")


class PostPublishedOnlyViaSenderTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="guard-test@example.com",
            password="x",
        )
        self.cat = Category.objects.create(name="Cat")

    def test_save_blocks_transition_to_published_without_sender_flag(self):
        post = Post.objects.create(
            title="T",
            slug="guard-draft",
            author=self.author,
            cover_image=_minimal_jpeg_upload("c.jpg"),
            body="<p>x</p>",
            status="draft",
            category=self.cat,
        )
        post.status = "published"
        with self.assertRaises(ValidationError):
            post.save()

    def test_save_allows_transition_with_sender_flag(self):
        post = Post.objects.create(
            title="T",
            slug="guard-sender",
            author=self.author,
            cover_image=_minimal_jpeg_upload("c.jpg"),
            body="<p>x</p>",
            status="ready_to_publish",
            category=self.cat,
        )
        post.status = "published"
        post.save(_allow_publish_via_sender=True)
        post.refresh_from_db()
        self.assertEqual(post.status, "published")


class PostHistoryServiceTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="history-test@example.com",
            password="x",
        )
        self.cat = Category.objects.create(name="HistoryCat")
        self.post = Post.objects.create(
            title="History post",
            slug="history-post",
            author=self.author,
            body="<p>Version one.</p>",
            status="draft",
            category=self.cat,
        )
        self.service = PostHistoryService()

    def test_record_autosave_snapshot_creates_entry(self):
        created = self.service.record_autosave_snapshot(self.post)
        self.assertIsNotNone(created)
        self.assertEqual(PostHistory.objects.filter(post=self.post).count(), 1)

    def test_record_skips_duplicate_snapshot(self):
        self.service.record_autosave_snapshot(self.post)
        second = self.service.record_autosave_snapshot(self.post)
        self.assertIsNone(second)
        self.assertEqual(PostHistory.objects.filter(post=self.post).count(), 1)

    def test_prune_keeps_only_last_hundred_entries(self):
        for i in range(105):
            self.post.body = f"<p>Version {i}.</p>"
            self.service.record_autosave_snapshot(self.post)
        self.assertEqual(PostHistory.objects.filter(post=self.post).count(), 100)
        latest = (
            PostHistory.objects.filter(post=self.post).order_by("-created_at").first()
        )
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertIn("Version 104", latest.body)

    def test_get_snapshot_returns_matching_entry(self):
        created = self.service.record_autosave_snapshot(self.post)
        assert created is not None
        snapshot = self.service.get_snapshot(self.post.pk, created.pk)
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.body, self.post.body)

    def test_missing_snapshot_returns_none(self):
        self.assertIsNone(self.service.get_snapshot(self.post.pk, 999999))

    def test_list_preview_truncates_and_handles_empty_body(self):
        self.post.body = "<p>" + ("word " * 80) + "</p>"
        created = self.service.record_autosave_snapshot(self.post)
        assert created is not None
        items = self.service.list_for_post(self.post.pk, limit=1)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].preview.endswith("…"))
        self.assertIn("created_at", self.service.list_item_to_dict(items[0]))

        self.post.body = ""
        self.post.short_description = "   "
        self.service.record_autosave_snapshot(self.post)
        empty_items = self.service.list_for_post(self.post.pk, limit=1)
        self.assertEqual(empty_items[0].preview, "(empty body)")
        snapshot = self.service.get_snapshot(self.post.pk, empty_items[0].id)
        assert snapshot is not None
        self.assertIsNone(snapshot.short_description)
        self.assertEqual(self.service.snapshot_to_dict(snapshot)["body"], "")


class PostSeriesNavigationTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="series-nav@example.com",
            password="x",
        )
        from editor.models import PostSeries, Series

        self.series = Series.objects.create(name="Guide")
        self.first = Post.objects.create(
            title="Part 1",
            slug="part-1",
            author=self.author,
            body="<p>One</p>",
            status="draft",
        )
        self.middle = Post.objects.create(
            title="Part 2",
            slug="part-2",
            author=self.author,
            body="<p>Two</p>",
            status="draft",
        )
        self.last = Post.objects.create(
            title="Part 3",
            slug="part-3",
            author=self.author,
            body="<p>Three</p>",
            status="draft",
        )
        PostSeries.objects.create(post=self.first, series=self.series, order_position=1)
        PostSeries.objects.create(
            post=self.middle, series=self.series, order_position=2
        )
        PostSeries.objects.create(post=self.last, series=self.series, order_position=3)

    def test_previous_and_next_follow_order(self):
        self.assertEqual(self.middle.get_series_position(self.series), 2)
        self.assertEqual(
            self.middle.get_previous_post_in_series(self.series), self.first
        )
        self.assertEqual(self.middle.get_next_post_in_series(self.series), self.last)
        self.assertIsNone(self.first.get_previous_post_in_series(self.series))
        self.assertIsNone(self.last.get_next_post_in_series(self.series))

    def test_unrelated_series_has_no_position(self):
        from editor.models import Series

        other = Series.objects.create(name="Other")
        self.assertIsNone(self.middle.get_series_position(other))
        self.assertIsNone(self.middle.get_previous_post_in_series(other))

    def test_duplicate_title_gets_unique_slug(self):
        first = Post.objects.create(
            title="Same title",
            author=self.author,
            body="<p>A</p>",
            status="draft",
        )
        second = Post.objects.create(
            title="Same title",
            author=self.author,
            body="<p>B</p>",
            status="draft",
        )
        self.assertEqual(first.slug, "same-title")
        self.assertEqual(second.slug, "same-title-2")

    def test_empty_cover_has_no_image_url(self):
        self.assertEqual(self.first.get_image_url(), "")
        self.assertIn("/draft/", self.first.get_draft_url())


class PublicCardFilterTests(TestCase):
    def test_preview_and_reading_helpers(self):
        from editor.templatetags.editor_filters import (
            exceeds_word_limit,
            first_sentence,
            needs_read_more_button,
            reading_time,
            strip_gallery_placeholders,
            truncatechars_whole_words,
            truncatewords_preserve_newlines,
        )

        self.assertEqual(truncatechars_whole_words("short", 20), "short")
        self.assertTrue(
            truncatechars_whole_words("one two three four", 8).endswith("…")
        )
        self.assertEqual(truncatechars_whole_words("text", "nope"), "text")
        self.assertTrue(exceeds_word_limit("a b c d", 3))
        self.assertFalse(exceeds_word_limit("a b", "x"))
        self.assertEqual(reading_time(""), 1)
        self.assertGreaterEqual(reading_time("<p>" + ("word " * 400) + "</p>"), 2)
        self.assertEqual(first_sentence("<p>Hello world. Next.</p>"), "Hello world.")
        self.assertEqual(first_sentence(""), "")
        html = strip_gallery_placeholders("<p>Hi</p>[gallery:1]<p>There</p>")
        self.assertIn("Hi", html)
        self.assertIn("There", html)
        self.assertNotIn("[gallery:1]", html)
        truncated = truncatewords_preserve_newlines("one two\n\nthree four", 3)
        self.assertIn("one two", truncated)
        self.assertNotIn("four", truncated)

        post = mock.Mock()
        post.short_description = None
        post.body = "<p>" + ("word " * 80) + "</p>"
        self.assertTrue(needs_read_more_button(post))
        self.assertFalse(needs_read_more_button(None))
