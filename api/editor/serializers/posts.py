"""Post and taxonomy serializers."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from blog.models import SitePublication
from editor.models import Category, Post, PostGalleryImage, Series

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ("id", "name", "slug")


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = serializers.StringRelatedField(many=True)
    is_on_site = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "status",
            "author",
            "category",
            "tags",
            "updated",
            "published",
            "is_on_site",
        )

    def get_is_on_site(self, obj: Post) -> bool:
        return SitePublication.objects.filter(post=obj).exists()


class PostGallerySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PostGalleryImage
        fields = ("id", "gallery_key", "image", "image_url", "caption", "order")

    def get_image_url(self, obj: PostGalleryImage) -> str:
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ""


class PostDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="author",
        write_only=True,
    )
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        allow_null=True,
        required=False,
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
    )
    series_ids = serializers.PrimaryKeyRelatedField(
        queryset=Series.objects.all(),
        many=True,
        source="series",
        write_only=True,
        required=False,
    )
    series = SeriesSerializer(many=True, read_only=True)
    gallery_images = PostGallerySerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    draft_preview_url = serializers.SerializerMethodField()
    is_on_site = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "slug",
            "uuid",
            "author",
            "author_id",
            "cover_image",
            "cover_image_url",
            "cover_image_credits",
            "cover_description",
            "body",
            "published",
            "status",
            "tags",
            "category",
            "category_id",
            "series",
            "series_ids",
            "short_description",
            "views",
            "gallery_images",
            "draft_preview_url",
            "is_on_site",
            "created",
            "updated",
        )
        read_only_fields = ("uuid", "views", "published", "created", "updated")

    def get_cover_image_url(self, obj: Post) -> str:
        if obj.cover_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return ""

    def get_draft_preview_url(self, obj: Post) -> str:
        request = self.context.get("request")
        path = obj.get_draft_url()
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_is_on_site(self, obj: Post) -> bool:
        return SitePublication.objects.filter(post=obj).exists()

    def _set_tags(self, instance: Post, tags: list[str] | None) -> None:
        if tags is not None:
            instance.tags.set(tags)

    def create(self, validated_data: dict[str, Any]) -> Post:
        tags = validated_data.pop("tags", None)
        instance = Post(**validated_data)
        instance.author = instance.author or self.context["request"].user
        instance.status = instance.status or "draft"
        instance.save()
        self._set_tags(instance, tags)
        return instance

    def update(self, instance: Post, validated_data: dict[str, Any]) -> Post:
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._set_tags(instance, tags)
        return instance


class PostWriteSerializer(serializers.Serializer):
    """Input for create/update via PostAdminForm service."""

    title = serializers.CharField(required=False, allow_blank=True)
    slug = serializers.CharField(required=False, allow_blank=True)
    author_id = serializers.IntegerField(required=False)
    body = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[c[0] for c in Post.STATUS_CHOICES],
        required=False,
    )
    short_description = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    category_id = serializers.IntegerField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
    )
    series_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    cover_image_credits = serializers.CharField(required=False, allow_blank=True)
    cover_description = serializers.CharField(required=False, allow_blank=True)
