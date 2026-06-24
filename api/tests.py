"""Editor API tests."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from editor.models import Post

User = get_user_model()


class EditorApiAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="editor@example.com",
            password="test-pass-123",
            is_staff=True,
        )

    def test_csrf_endpoint(self):
        response = self.client.get("/api/editor/v1/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.json())

    def test_login_and_me(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        login = self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "editor@example.com", "password": "test-pass-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(login.status_code, 200)
        me = self.client.get("/api/editor/v1/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "editor@example.com")

    def test_posts_require_staff(self):
        response = self.client.get("/api/editor/v1/posts/")
        self.assertEqual(response.status_code, 403)


class EditorApiPostTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="staff@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_create_draft_post(self):
        response = self.client.post(
            "/api/editor/v1/posts/",
            {"body": "<p>Hello world</p>", "title": "Test"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.get().status, "draft")

    def test_cannot_set_published_via_api(self):
        post = Post.objects.create(
            author=self.user,
            title="T",
            slug="t",
            body="<p>x</p>",
            status="ready_to_publish",
        )
        response = self.client.patch(
            f"/api/editor/v1/posts/{post.pk}/",
            {"status": "published"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_openapi_schema(self):
        response = self.client.get("/api/editor/v1/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.json())

    def test_text_quality(self):
        response = self.client.post(
            "/api/editor/v1/posts/text-quality/",
            {
                "text": "<p>Короткий тестовый текст для проверки качества.</p>",
                "locale": "ru-RU",
                "content_format": "html",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("ok"))

    def test_list_posts_after_login(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "staff@example.com", "password": "test-pass-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        response = self.client.get("/api/editor/v1/posts/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
