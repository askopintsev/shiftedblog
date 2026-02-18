import datetime
import os
import uuid
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from taggit.managers import TaggableManager


def validate_image_extension(value):
    valid_extensions = [".jpg", ".jpeg", ".png"]
    ext = os.path.splitext(value.name.lower())[1]
    if ext not in valid_extensions:
        raise ValidationError(
            "Unsupported file extension. Only JPG, JPEG, and PNG are allowed."
        )


class Category(models.Model):
    """Model for post categories list"""

    name = models.CharField(max_length=250)

    class Meta:
        app_label = "editor"
        db_table = "editor_category"

    def __str__(self):
        return self.name


class Series(models.Model):
    """Model for post series list"""

    name = models.CharField(max_length=250)

    class Meta:
        app_label = "editor"
        db_table = "editor_series"

    def __str__(self):
        return self.name


class PostSeries(models.Model):
    """Through model for Post and Series with order position"""

    post = models.ForeignKey(
        "Post",
        on_delete=models.CASCADE,
        related_name="post_series",
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name="series_posts",
    )
    order_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Order position in series",
    )

    class Meta:
        app_label = "editor"
        db_table = "editor_postseries"
        unique_together: ClassVar[list] = [["series", "order_position"]]
        ordering: ClassVar[list] = ["series", "order_position"]

    def __str__(self):
        return (
            f"{self.series.name} - {self.post.title} (Position: {self.order_position})"
        )


class Post(models.Model):
    """Model for post objects"""

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("ready_to_publish", "Ready to publish"),
        ("published", "Published"),
    )

    title = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=250,
        unique=True,
    )
    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Secret UUID for draft preview URL.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blog_posts",
    )
    cover_image = models.ImageField(
        upload_to="img/post/" + datetime.datetime.today().strftime("%Y/%m/%d"),
        validators=[validate_image_extension],
    )
    cover_image_credits = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        default=None,
    )
    cover_description = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        default=None,
    )
    body = models.TextField()
    published = models.DateTimeField(null=True, blank=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="draft",
    )
    tags = TaggableManager()
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="blog_category",
    )
    series = models.ManyToManyField(
        Series,
        through="PostSeries",
        related_name="blog_series",
        blank=True,
    )
    short_description = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        default=None,
    )
    views = models.PositiveIntegerField(
        default=0,
        verbose_name="Views count",
    )

    class Meta:
        app_label = "editor"
        db_table = "editor_post"
        ordering = (
            "-published",
            "-created",
        )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Automatically set published date when status changes to 'published'."""
        if self.status == "published" and self.published is None:
            self.published = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("editor:post_detail", args=[self.slug])

    def get_draft_url(self):
        """Secret URL to view this post (including drafts) by UUID."""
        return reverse("editor:post_detail_by_uuid", args=[self.uuid])

    def draft_preview_link(self):
        """Clickable link to open post as draft (for admin readonly display)."""
        url = self.get_draft_url()
        return mark_safe(
            f'<a href="{url}" target="_blank" rel="noopener">View draft</a>'
        )

    draft_preview_link.short_description = "Draft preview link"

    def get_image_url(self):
        return str(self.cover_image)

    def get_series_position(self, series):
        """Get the order position of this post in a given series"""
        try:
            post_series = PostSeries.objects.get(post=self, series=series)
            return post_series.order_position
        except PostSeries.DoesNotExist:
            return None

    def get_previous_post_in_series(self, series):
        """Get the previous post in the series based on order position"""
        try:
            current_position = self.get_series_position(series)
            if current_position is None:
                return None

            previous_post_series = (
                PostSeries.objects.filter(
                    series=series,
                    order_position__lt=current_position,
                )
                .order_by("-order_position")
                .first()
            )

            if previous_post_series:
                return previous_post_series.post
            return None
        except Exception:
            return None

    def get_next_post_in_series(self, series):
        """Get the next post in the series based on order position"""
        try:
            current_position = self.get_series_position(series)
            if current_position is None:
                return None

            next_post_series = (
                PostSeries.objects.filter(
                    series=series,
                    order_position__gt=current_position,
                )
                .order_by("order_position")
                .first()
            )

            if next_post_series:
                return next_post_series.post
            return None
        except Exception:
            return None


class PostGalleryImage(models.Model):
    """Image for a post body carousel gallery. Use gallery_key to group images.
    Insert [gallery:1], [gallery:2], ... in the post body where the gallery should appear."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    gallery_key = models.PositiveIntegerField(
        default=1,
        help_text="Gallery number. Use [gallery:1] in the body for this gallery, [gallery:2] for the next, etc.",
    )
    image = models.ImageField(
        upload_to="img/post/gallery/%Y/%m/%d",
        validators=[validate_image_extension],
    )
    caption = models.CharField(
        max_length=250,
        blank=True,
        default="",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within this gallery (lower first).",
    )

    class Meta:
        app_label = "editor"
        db_table = "editor_postgalleryimage"
        ordering = ["gallery_key", "order", "id"]

    def __str__(self):
        return f"Gallery {self.gallery_key} image {self.order} for {self.post.title}"
