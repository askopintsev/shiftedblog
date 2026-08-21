"""Editor API tests."""

import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from editor.models import Post, PostSeries, Series

User = get_user_model()


def _minimal_jpeg_upload(name: str = "cover.jpg") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


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

    def test_login_rejects_wrong_password(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "editor@example.com", "password": "wrong-password"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["ok"])

    def test_login_accepts_email_with_uppercase_domain(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "editor@EXAMPLE.com", "password": "test-pass-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["step"], "complete")

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

    def test_patch_cover_image(self):
        post = Post.objects.create(
            author=self.user,
            title="Cover test",
            slug="cover-test",
            body="<p>Body</p>",
            status="draft",
        )
        response = self.client.patch(
            f"/api/editor/v1/posts/{post.pk}/",
            {"cover_image": _minimal_jpeg_upload()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertTrue(post.cover_image.name)
        self.assertTrue(
            response.json()["post"]["cover_image_url"].startswith("/media/")
        )

    def test_gallery_upload_rejects_invalid_image(self):
        post = Post.objects.create(
            author=self.user,
            title="Bad gallery upload",
            slug="bad-gallery-upload",
            body="<p>Body</p>",
            status="draft",
        )
        response = self.client.post(
            f"/api/editor/v1/posts/{post.pk}/gallery/",
            {
                "gallery_key": "1",
                "image": SimpleUploadedFile(
                    "broken.jpg",
                    b"not an image",
                    content_type="image/jpeg",
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(Post.objects.get(pk=post.pk).gallery_images.count(), 0)

    def test_clear_cover_image(self):
        post = Post.objects.create(
            author=self.user,
            title="Clear cover test",
            slug="clear-cover-test",
            body="<p>Body</p>",
            status="draft",
            cover_image=_minimal_jpeg_upload(),
        )
        self.assertTrue(post.cover_image.name)
        response = self.client.patch(
            f"/api/editor/v1/posts/{post.pk}/",
            {"cover_image_clear": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertFalse(post.cover_image.name)
        self.assertEqual(response.json()["post"]["cover_image_url"], "")

    def test_patch_tags(self):
        post = Post.objects.create(
            author=self.user,
            title="Tags test",
            slug="tags-test",
            body="<p>Body</p>",
            status="draft",
        )
        response = self.client.patch(
            f"/api/editor/v1/posts/{post.pk}/",
            {"tags": ["news", "django", "анимация"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(
            sorted(post.tags.names()),
            ["django", "news", "анимация"],
        )
        self.assertEqual(
            sorted(response.json()["post"]["tags"]),
            ["django", "news", "анимация"],
        )

    def test_openapi_schema(self):
        response = self.client.get("/api/editor/v1/schema/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("openapi", body)

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


class EditorApiMediaUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="media@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def _png_bytes(self) -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), color="blue").save(buffer, format="PNG")
        return buffer.getvalue()

    def test_upload_with_filename(self):
        uploaded = SimpleUploadedFile(
            "shot.png",
            self._png_bytes(),
            content_type="image/png",
        )
        response = self.client.post(
            "/api/editor/v1/media/upload/",
            {"upload": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["uploaded"], 1)
        self.assertTrue(payload["url"].endswith(".png"))

    def test_clipboard_upload_without_extension_uses_content_type(self):
        # Browsers often paste clipboard images with an empty/extension-less name.
        uploaded = SimpleUploadedFile(
            "image",
            self._png_bytes(),
            content_type="image/png",
        )
        response = self.client.post(
            "/api/editor/v1/media/upload/",
            {"upload": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["uploaded"], 1)
        self.assertTrue(str(payload["fileName"]).endswith(".png"))
        self.assertTrue(payload["url"].endswith(".png"))

    def test_upload_rejects_unknown_type(self):
        uploaded = SimpleUploadedFile(
            "notes",
            b"not-an-image",
            content_type="text/plain",
        )
        response = self.client.post(
            "/api/editor/v1/media/upload/",
            {"upload": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)


class EditorSiteSettingsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="sitesettings@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_get_and_patch_site_settings(self):
        get_response = self.client.get("/api/editor/v1/config/site-settings/")
        self.assertEqual(get_response.status_code, 200)
        self.assertTrue(get_response.json()["ok"])
        self.assertIn("site_name", get_response.json()["settings"])

        patch_response = self.client.patch(
            "/api/editor/v1/config/site-settings/",
            {"site_name": "Editor Site"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["settings"]["site_name"], "Editor Site")

        again = self.client.get("/api/editor/v1/config/site-settings/")
        self.assertEqual(again.json()["settings"]["site_name"], "Editor Site")


class EditorTagListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="tags@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        post = Post.objects.create(
            title="Tagged",
            slug="tagged-post",
            author=self.user,
            status="draft",
            body="<p>hi</p>",
        )
        post.tags.set(["django", "news"])

    def test_lists_existing_tag_names(self):
        response = self.client.get("/api/editor/v1/tags/")
        self.assertEqual(response.status_code, 200)
        names = response.json()["results"]
        self.assertIn("django", names)
        self.assertIn("news", names)

    def test_filters_by_query(self):
        response = self.client.get("/api/editor/v1/tags/", {"q": "dja"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], ["django"])


class EditorSeriesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="series@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.series = Series.objects.create(name="Roadmap")
        self.post = Post.objects.create(
            title="Part one",
            slug="part-one",
            author=self.user,
            status="draft",
            body="<p>hi</p>",
        )

    def test_create_series_and_assign_with_position(self):
        create = self.client.post(
            "/api/editor/v1/series/",
            {"name": "New series"},
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        series_id = create.json()["series"]["id"]

        patch = self.client.patch(
            f"/api/editor/v1/posts/{self.post.pk}/",
            {"series_id": series_id, "series_order_position": 2},
            format="json",
        )
        self.assertEqual(patch.status_code, 200)
        memberships = patch.json()["post"]["series"]
        self.assertEqual(len(memberships), 1)
        self.assertEqual(memberships[0]["id"], series_id)
        self.assertEqual(memberships[0]["order_position"], 2)

        row = PostSeries.objects.get(post=self.post)
        self.assertEqual(row.series_id, series_id)
        self.assertEqual(row.order_position, 2)

    def test_clear_series_membership(self):
        PostSeries.objects.create(
            post=self.post,
            series=self.series,
            order_position=1,
        )
        patch = self.client.patch(
            f"/api/editor/v1/posts/{self.post.pk}/",
            {"series_id": None, "series_order_position": None},
            format="json",
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()["post"]["series"], [])
        self.assertFalse(PostSeries.objects.filter(post=self.post).exists())
