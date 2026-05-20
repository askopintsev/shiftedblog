import json
from typing import cast

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from core.models.user import User, UserManager
from editor.models import Category, Post
from editor.text_quality_service import PostTextQualityService, TextQualityRequestDTO


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
        self.assertGreaterEqual(punctuation_score, 60)

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
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
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
            cover_image=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
            body="<p>x</p>",
            status="ready_to_publish",
            category=self.cat,
        )
        post.status = "published"
        post.save(_allow_publish_via_sender=True)
        post.refresh_from_db()
        self.assertEqual(post.status, "published")
