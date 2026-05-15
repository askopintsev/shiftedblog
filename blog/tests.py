from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from blog.models import SitePublication
from editor.models import Category, Post


class BlogPublicVisibilityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.author = user_model.objects.create_user(
            email="author@example.com",
            password="example-pass-123",
        )
        self.category = Category.objects.create(name="Blog")

        self.visible_post = Post.objects.create(
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
        SitePublication.objects.create(
            post=self.visible_post, published_at=self.visible_post.published
        )

        self.hidden_post = Post.objects.create(
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
