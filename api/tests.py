"""Editor API tests."""

import io
from unittest import mock

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from blog.models import SitePublication
from core.models.network import (
    NETWORK_SLUG_SITE,
    NETWORK_SLUG_TELEGRAM,
    Credential,
    Network,
)
from core.models.telegram_settings import TelegramNetworkSettings
from editor.models import (
    Category,
    Post,
    PostGalleryImage,
    PostHistory,
    PostSeries,
    Series,
)
from sender.models.post_link import PostLink

User = get_user_model()

_FERNET_TEST_KEY = Fernet.generate_key().decode("ascii")


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


class EditorApiAuthEdgeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            email="staff-auth@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.reader = User.objects.create_user(
            email="reader@example.com",
            password="test-pass-123",
            is_staff=False,
        )

    def test_login_rejects_empty_email(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "  ", "password": "test-pass-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 401)

    def test_login_rejects_non_staff(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        response = self.client.post(
            "/api/editor/v1/auth/login/",
            {"email": "reader@example.com", "password": "test-pass-123"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Staff", response.json()["error"])

    def test_login_with_2fa_device_returns_2fa_step(self):
        csrf = self.client.get("/api/editor/v1/auth/csrf/").json()["csrfToken"]
        with mock.patch("api.editor.views.auth.user_has_device", return_value=True):
            response = self.client.post(
                "/api/editor/v1/auth/login/",
                {"email": "staff-auth@example.com", "password": "test-pass-123"},
                format="json",
                HTTP_X_CSRFTOKEN=csrf,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["step"], "2fa")

    def test_2fa_verify_rejects_invalid_token(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            "/api/editor/v1/auth/2fa/verify/",
            {"token": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_logout_and_session_keepalive(self):
        self.client.force_login(self.staff)
        keepalive = self.client.get("/api/editor/v1/auth/session-keepalive/")
        self.assertEqual(keepalive.status_code, 204)
        logout = self.client.post("/api/editor/v1/auth/logout/")
        self.assertEqual(logout.status_code, 200)
        after = self.client.get("/api/editor/v1/posts/")
        self.assertEqual(after.status_code, 403)


class EditorApiPostWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="workflow@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="News")
        self.post = Post.objects.create(
            author=self.user,
            title="Workflow post",
            slug="workflow-post",
            body="<p>Body</p>",
            status="draft",
            category=self.category,
        )

    def test_get_post_detail_includes_draft_preview_url(self):
        response = self.client.get(f"/api/editor/v1/posts/{self.post.pk}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["post"]
        self.assertEqual(payload["slug"], "workflow-post")
        self.assertIn("/draft/", payload["draft_preview_url"])

    def test_list_filters_by_status_and_search(self):
        Post.objects.create(
            author=self.user,
            title="Other draft",
            slug="other-draft",
            body="<p>x</p>",
            status="draft",
        )
        ready = Post.objects.create(
            author=self.user,
            title="Ready item",
            slug="ready-item",
            body="<p>x</p>",
            status="ready_to_publish",
        )
        by_status = self.client.get(
            "/api/editor/v1/posts/", {"status": "ready_to_publish"}
        )
        self.assertEqual(by_status.status_code, 200)
        ids = [row["id"] for row in by_status.json()["results"]]
        self.assertEqual(ids, [ready.pk])

        by_search = self.client.get("/api/editor/v1/posts/", {"search": "workflow"})
        titles = [row["title"] for row in by_search.json()["results"]]
        self.assertEqual(titles, ["Workflow post"])

    def test_autosave_records_history_and_history_endpoints(self):
        save = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/autosave/",
            {"body": "<p>Autosaved body with enough text.</p>"},
            format="json",
        )
        self.assertEqual(save.status_code, 200)
        self.assertTrue(save.json()["ok"])
        history_row = PostHistory.objects.get(post=self.post)

        listing = self.client.get(f"/api/editor/v1/posts/{self.post.pk}/history/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["items"][0]["id"], history_row.pk)

        detail = self.client.get(
            f"/api/editor/v1/posts/{self.post.pk}/history/{history_row.pk}/"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Autosaved body", detail.json()["snapshot"]["body"])

        missing = self.client.get(
            f"/api/editor/v1/posts/{self.post.pk}/history/999999/"
        )
        self.assertEqual(missing.status_code, 404)

    def test_text_quality_requires_text(self):
        response = self.client.post(
            "/api/editor/v1/posts/text-quality/",
            {"text": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])

    def test_gallery_create_patch_and_delete(self):
        created = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/gallery/",
            {
                "gallery_key": "1",
                "caption": "First",
                "image": _minimal_jpeg_upload("g1.jpg"),
            },
            format="multipart",
        )
        self.assertEqual(created.status_code, 201)
        gallery_id = created.json()["gallery"]["id"]

        listed = self.client.get(f"/api/editor/v1/posts/{self.post.pk}/gallery/")
        self.assertEqual(len(listed.json()["results"]), 1)

        patched = self.client.patch(
            f"/api/editor/v1/posts/{self.post.pk}/gallery/{gallery_id}/",
            {"caption": "Updated"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["gallery"]["caption"], "Updated")

        deleted = self.client.delete(
            f"/api/editor/v1/posts/{self.post.pk}/gallery/{gallery_id}/"
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(PostGalleryImage.objects.filter(post=self.post).count(), 0)

    def test_gallery_rejects_empty_image(self):
        response = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/gallery/",
            {
                "gallery_key": "1",
                "image": SimpleUploadedFile(
                    "empty.jpg",
                    b"",
                    content_type="image/jpeg",
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["error"].lower())

    def test_gallery_requires_image_file(self):
        response = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/gallery/",
            {"gallery_key": "1"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_categories_list_create_and_patch(self):
        listed = self.client.get("/api/editor/v1/categories/")
        names = [row["name"] for row in listed.json()["results"]]
        self.assertIn("News", names)

        created = self.client.post(
            "/api/editor/v1/categories/",
            {"name": "Essays", "slug": "essays"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        category_id = created.json()["category"]["id"]

        patched = self.client.patch(
            f"/api/editor/v1/categories/{category_id}/",
            {"name": "Essays updated"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["category"]["name"], "Essays updated")

    def test_series_list_and_patch(self):
        listed = self.client.get("/api/editor/v1/series/")
        self.assertEqual(listed.status_code, 200)
        series = Series.objects.create(name="Rename me")
        patched = self.client.patch(
            f"/api/editor/v1/series/{series.pk}/",
            {"name": "Renamed"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["series"]["name"], "Renamed")

    def test_series_position_conflict_is_rejected(self):
        series = Series.objects.create(name="Conflict")
        other = Post.objects.create(
            author=self.user,
            title="Other",
            slug="other-series-post",
            body="<p>x</p>",
            status="draft",
        )
        PostSeries.objects.create(post=other, series=series, order_position=1)
        response = self.client.patch(
            f"/api/editor/v1/posts/{self.post.pk}/",
            {"series_id": series.pk, "series_order_position": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("series_order_position", response.json()["errors"])

    def test_unknown_series_is_rejected(self):
        response = self.client.patch(
            f"/api/editor/v1/posts/{self.post.pk}/",
            {"series_id": 999999},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("series_id", response.json()["errors"])

    def test_site_publish_requires_published_status(self):
        response = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/site-publish/"
        )
        self.assertEqual(response.status_code, 400)

        self.post.status = "published"
        self.post.save(_allow_publish_via_sender=True)
        published = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/site-publish/"
        )
        self.assertEqual(published.status_code, 200)
        self.assertTrue(SitePublication.objects.filter(post=self.post).exists())

        unpublished = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/site-unpublish/"
        )
        self.assertEqual(unpublished.status_code, 200)
        self.assertFalse(SitePublication.objects.filter(post=self.post).exists())

    @override_settings(PUBLIC_SITE_ENABLED=False)
    def test_site_publish_disabled_when_public_site_off(self):
        response = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/site-publish/"
        )
        self.assertEqual(response.status_code, 403)
        unpublish = self.client.post(
            f"/api/editor/v1/posts/{self.post.pk}/site-unpublish/"
        )
        self.assertEqual(unpublish.status_code, 403)


class EditorApiPublishTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="publisher@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            title="Ready to ship",
            slug="ready-to-ship",
            body="<p>Body</p>",
            status="ready_to_publish",
            cover_image=_minimal_jpeg_upload("cover.jpg"),
        )
        Network.objects.get_or_create(
            slug=NETWORK_SLUG_SITE,
            defaults={"name": "Site"},
        )

    def test_ready_posts_list(self):
        response = self.client.get("/api/editor/v1/publish/ready/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()["results"]]
        self.assertIn(self.post.pk, ids)

    def test_publish_to_site_creates_publication(self):
        response = self.client.post(
            "/api/editor/v1/publish/",
            {
                "post_id": self.post.pk,
                "dest_site": True,
                "dest_telegram": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, "published")
        self.assertTrue(SitePublication.objects.filter(post=self.post).exists())

    @override_settings(PUBLIC_SITE_ENABLED=False)
    def test_publish_site_forbidden_when_public_site_disabled(self):
        response = self.client.post(
            "/api/editor/v1/publish/",
            {"post_id": self.post.pk, "dest_site": True},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])

    def test_telegram_preview_returns_cards(self):
        response = self.client.get(
            "/api/editor/v1/publish/telegram-preview/",
            {"post_id": self.post.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertIn("preview_payload", response.json())

    def test_telegram_preview_missing_post_is_404(self):
        response = self.client.get(
            "/api/editor/v1/publish/telegram-preview/",
            {"post_id": 999999},
        )
        self.assertEqual(response.status_code, 404)

    def test_story_availability_without_operator_session(self):
        response = self.client.get("/api/editor/v1/publish/story-availability/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])


@override_settings(CREDENTIALS_ENCRYPTION_KEY=_FERNET_TEST_KEY)
class EditorApiConfigTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            email="config-staff@example.com",
            password="test-pass-123",
            is_staff=True,
        )
        self.superuser = User.objects.create_user(
            email="config-admin@example.com",
            password="test-pass-123",
            is_staff=True,
            is_superuser=True,
        )
        self.site_net, _ = Network.objects.get_or_create(
            slug=NETWORK_SLUG_SITE,
            defaults={"name": "Site"},
        )
        self.tg_net, _ = Network.objects.get_or_create(
            slug=NETWORK_SLUG_TELEGRAM,
            defaults={"name": "Telegram"},
        )

    def test_staff_can_list_and_rename_network(self):
        self.client.force_login(self.staff)
        listed = self.client.get("/api/editor/v1/config/networks/")
        slugs = [row["slug"] for row in listed.json()["results"]]
        self.assertIn(NETWORK_SLUG_SITE, slugs)

        patched = self.client.patch(
            f"/api/editor/v1/config/networks/{self.site_net.pk}/",
            {"name": "Public site"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["network"]["name"], "Public site")

    def test_staff_cannot_read_credentials(self):
        self.client.force_login(self.staff)
        response = self.client.get("/api/editor/v1/config/credentials/")
        self.assertEqual(response.status_code, 403)

    def test_superuser_credential_crud_masks_secrets(self):
        self.client.force_login(self.superuser)
        created = self.client.post(
            "/api/editor/v1/config/credentials/",
            {
                "network": self.tg_net.pk,
                "label": "prod bot",
                "secrets": {"bot_token": "secret-token", "channel_name": "chan"},
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        cred_id = created.json()["credential"]["id"]
        self.assertEqual(
            created.json()["credential"]["secrets_masked"]["bot_token"],
            "••••••",
        )

        listed = self.client.get("/api/editor/v1/config/credentials/")
        self.assertEqual(len(listed.json()["results"]), 1)

        detail = self.client.get(f"/api/editor/v1/config/credentials/{cred_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.json()["credential"]["secrets_masked"]["channel_name"],
            "••••••",
        )

        patched = self.client.patch(
            f"/api/editor/v1/config/credentials/{cred_id}/",
            {"label": "prod bot 2", "secrets": {"bot_token": "new-token"}},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["credential"]["label"], "prod bot 2")
        cred = Credential.objects.get(pk=cred_id)
        self.assertEqual(cred.get_secrets_dict()["bot_token"], "new-token")

        deleted = self.client.delete(f"/api/editor/v1/config/credentials/{cred_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Credential.objects.filter(pk=cred_id).exists())

    def test_telegram_settings_get_and_patch(self):
        self.client.force_login(self.staff)
        TelegramNetworkSettings.objects.all().delete()
        empty = self.client.get("/api/editor/v1/config/telegram-settings/")
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.json()["settings"])

        missing = self.client.patch(
            "/api/editor/v1/config/telegram-settings/",
            {"post_continuation_text": "Continued:"},
            format="json",
        )
        self.assertEqual(missing.status_code, 404)

        TelegramNetworkSettings.objects.create(network=self.tg_net)
        patched = self.client.patch(
            "/api/editor/v1/config/telegram-settings/",
            {"post_continuation_text": "Continued:"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(
            patched.json()["settings"]["post_continuation_text"],
            "Continued:",
        )

    def test_post_link_audit_filters(self):
        self.client.force_login(self.staff)
        post = Post.objects.create(
            author=self.staff,
            title="Linked",
            slug="linked-post",
            body="<p>x</p>",
            status="draft",
        )
        PostLink.objects.create(
            post=post,
            network=self.site_net,
            message_url="https://example.org/linked-post/",
        )
        listed = self.client.get(
            "/api/editor/v1/audit/post-links/",
            {"post_id": str(post.pk), "network": NETWORK_SLUG_SITE},
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["results"]), 1)
        self.assertEqual(
            listed.json()["results"][0]["message_url"],
            "https://example.org/linked-post/",
        )
