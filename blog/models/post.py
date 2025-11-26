import datetime
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from taggit.managers import TaggableManager


def validate_image_extension(value):
    valid_extensions = ['.jpg', '.jpeg', '.png']
    ext = os.path.splitext(value.name.lower())[1]
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension. Only JPG, JPEG, and PNG are allowed.')


class Category(models.Model):
    """Model for post categories list"""
    name = models.CharField(max_length=250)

    class Meta:
        app_label = 'blog'

    def __str__(self):
        return self.name
    

class Series(models.Model):
    """Model for post series list"""
    name = models.CharField(max_length=250)

    class Meta:
        app_label = 'blog'

    def __str__(self):
        return self.name


class Post(models.Model):
    """Model for post objects"""

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=250,
        unique=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='blog_posts',
    )
    cover_image = models.ImageField(
        upload_to='img/post/' + datetime.datetime.today().strftime('%Y/%m/%d'),
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
    published = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
    )
    tags = TaggableManager()
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='blog_category',
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='blog_series',
        null=True,
        blank=True,
        default=None,
    )
    short_description = models.CharField(
        max_length=300,
        null=True,
        blank=True,
        default=None,
    )
    views = models.PositiveIntegerField(
        default=0,
        verbose_name='Views count',
    )

    class Meta:
        app_label = 'blog'
        ordering = ('-published',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            'blog:post_detail',
            args=[self.slug],
        )

    def get_image_url(self):
        return str(self.cover_image)
