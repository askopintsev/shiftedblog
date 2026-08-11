"""Post and taxonomy serializers."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.editor.media_urls import relative_media_url
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
        fields = ("id", "name")


class PostSeriesMembershipSerializer(serializers.Serializer):
    """Series membership for a post, including order in the series."""

    id = serializers.IntegerField(source="series_id", read_only=True)
    name = serializers.CharField(source="series.name", read_only=True)
    order_position = serializers.IntegerField(allow_null=True, required=False)


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
        return relative_media_url(obj.image)


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
    tags = serializers.StringRelatedField(many=True, required=False)
    series = serializers.SerializerMethodField()
    gallery_images = PostGallerySerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
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
        return relative_media_url(obj.cover_image)

    def get_cover_image(self, obj: Post) -> str | None:
        url = relative_media_url(obj.cover_image)
        return url or None

    def get_draft_preview_url(self, obj: Post) -> str:
        request = self.context.get("request")
        path = obj.get_draft_url()
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_is_on_site(self, obj: Post) -> bool:
        return SitePublication.objects.filter(post=obj).exists()

    def get_series(self, obj: Post) -> list[dict[str, Any]]:
        memberships = getattr(obj, "_prefetched_objects_cache", {}).get("post_series")
        if memberships is None:
            qs = obj.post_series.select_related("series").order_by(
                "order_position",
                "pk",
            )
        else:
            qs = sorted(
                memberships,
                key=lambda row: (
                    row.order_position is None,
                    row.order_position or 0,
                    row.pk,
                ),
            )
        data = PostSeriesMembershipSerializer(qs, many=True).data
        return list(data)

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
    series_id = serializers.IntegerField(required=False, allow_null=True)
    series_order_position = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )
    cover_image_credits = serializers.CharField(required=False, allow_blank=True)
    cover_description = serializers.CharField(required=False, allow_blank=True)
    cover_image_clear = serializers.BooleanField(required=False)
