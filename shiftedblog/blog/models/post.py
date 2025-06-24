import datetime

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone

from taggit.managers import TaggableManager


class Category(models.Model):
    """Model for post categories list"""
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class Post(models.Model):
    """Model for post objects"""

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250,
                            unique_for_date='published')
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='blog_posts')
    cover_image = models.ImageField(upload_to='img/post/' + datetime.datetime.today().strftime('%Y/%m/%d'))
    cover_image_credits = models.CharField(max_length=250, null=True, blank=True)
    cover_description = models.CharField(max_length=250)
    body = models.TextField()
    published = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,
                              choices=STATUS_CHOICES,
                              default='draft')
    tags = TaggableManager()
    category = models.ForeignKey(Category,
                                 on_delete=models.CASCADE,
                                 related_name='blog_category')
    short_description = models.CharField(max_length=300)

    class Meta:
        ordering = ('-published',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail',
                       args=[self.published.year,
                             self.published.month,
                             self.published.day,
                             self.slug])

    def get_image_url(self):
        return str(self.cover_image)
