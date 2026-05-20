import io
from typing import cast

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from blog.models import SitePublication
from core.models.user import User, UserManager
from editor.models import Category, Post
from sender.services.url_helpers import post_og_image_absolute_url


def _minimal_jpeg_upload(name: str = "cover.jpg") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (120, 80), color=(200, 40, 40)).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class BlogPublicVisibilityTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="author@example.com",
            password="example-pass-123",
        )
        self.category = Category.objects.create(name="Blog")

        self.visible_post = Post(
            title="Visible post",
            slug="visible-post",
            author=self.author,
            cover_image=SimpleUploadedFile(
                "cover-visible.jpg",
                b"filecontent",
                content_type="image/jpeg",
            ),
            body="Visible body",
            status="published",
            category=self.category,
        )
        self.visible_post.save(_allow_publish_via_sender=True)
        SitePublication.objects.create(
            post=self.visible_post, published_at=self.visible_post.published
        )

        self.hidden_post = Post(
            title="Hidden post",
            slug="hidden-post",
            author=self.author,
            cover_image=SimpleUploadedFile(
                "cover-hidden.jpg",
                b"filecontent",
                content_type="image/jpeg",
            ),
            body="Hidden body",
            status="published",
            category=self.category,
        )
        self.hidden_post.save(_allow_publish_via_sender=True)

    def test_list_view_shows_only_site_published_posts(self):
        response = self.client.get(reverse("blog:post_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visible_post.title)
        self.assertNotContains(response, self.hidden_post.title)

    def test_detail_view_requires_site_publication(self):
        visible_response = self.client.get(
            reverse("blog:post_detail", args=[self.visible_post.slug])
        )
        self.assertEqual(visible_response.status_code, 200)

        hidden_response = self.client.get(
            reverse("blog:post_detail", args=[self.hidden_post.slug])
        )
        self.assertEqual(hidden_response.status_code, 404)

    def test_draft_preview_route_stays_under_editor_namespace(self):
        response = self.client.get(
            reverse("editor:post_detail_by_uuid", args=[self.visible_post.uuid])
        )
        self.assertEqual(response.status_code, 200)


class PostSocialShareImageTests(TestCase):
    def setUp(self):
        self.author = cast(UserManager, User.objects).create_user(
            email="share-test@example.com",
            password="secret12345",
        )
        self.category = Category.objects.create(name="Share")
        self.post = Post(
            title="Share image post",
            slug="share-image-post",
            author=self.author,
            cover_image=_minimal_jpeg_upload(),
            body="<p>Body</p>",
            status="published",
            category=self.category,
        )
        self.post.save(_allow_publish_via_sender=True)
        SitePublication.objects.create(
            post=self.post,
            published_at=self.post.published,
        )

    def test_detail_page_uses_jpeg_og_image_url(self):
        response = self.client.get(
            reverse("blog:post_detail", args=[self.post.slug]),
        )
        self.assertEqual(response.status_code, 200)
        expected = post_og_image_absolute_url(self.post, response.wsgi_request)
        self.assertIsNotNone(expected)
        assert expected is not None
        self.assertContains(response, f'property="og:image" content="{expected}"')
        self.assertContains(response, f'name="twitter:image" content="{expected}"')
        self.assertNotContains(response, ".avif")

    def test_og_image_endpoint_returns_jpeg(self):
        url = reverse("blog:post_og_image", args=[self.post.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertTrue(response.content.startswith(b"\xff\xd8"))


class FeedLentaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.reader = cast(UserManager, User.objects).create_user(
            email="feedreader@example.com",
            password="secret12345",
        )

    def test_feed_redirects_when_not_logged_in(self):
        response = self.client.get(reverse("blog:post_lenta"))
        self.assertEqual(response.status_code, 302)

    def test_feed_renders_for_logged_in_user(self):
        self.client.login(email="feedreader@example.com", password="secret12345")
        response = self.client.get(reverse("blog:post_lenta"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Лента")
