from django.urls import path

from api.editor.views import auth, config, media, posts, publish

app_name = "api_editor"

urlpatterns = [
    path("auth/csrf/", auth.CsrfView.as_view(), name="csrf"),
    path("auth/login/", auth.LoginView.as_view(), name="login"),
    path("auth/2fa/verify/", auth.TwoFactorVerifyView.as_view(), name="2fa_verify"),
    path("auth/logout/", auth.LogoutView.as_view(), name="logout"),
    path("auth/me/", auth.MeView.as_view(), name="me"),
    path(
        "auth/session-keepalive/",
        auth.SessionKeepaliveView.as_view(),
        name="session_keepalive",
    ),
    path("posts/", posts.PostListCreateView.as_view(), name="post_list"),
    path("posts/text-quality/", posts.TextQualityView.as_view(), name="text_quality"),
    path("posts/<int:post_id>/", posts.PostDetailView.as_view(), name="post_detail"),
    path(
        "posts/<int:post_id>/autosave/",
        posts.PostAutosaveView.as_view(),
        name="post_autosave",
    ),
    path(
        "posts/<int:post_id>/history/",
        posts.PostHistoryListView.as_view(),
        name="post_history_list",
    ),
    path(
        "posts/<int:post_id>/history/<int:history_id>/",
        posts.PostHistoryDetailView.as_view(),
        name="post_history_detail",
    ),
    path(
        "posts/<int:post_id>/site-publish/",
        posts.PostSitePublishView.as_view(),
        name="post_site_publish",
    ),
    path(
        "posts/<int:post_id>/site-unpublish/",
        posts.PostSiteUnpublishView.as_view(),
        name="post_site_unpublish",
    ),
    path(
        "posts/<int:post_id>/gallery/",
        posts.PostGalleryListCreateView.as_view(),
        name="post_gallery_list",
    ),
    path(
        "posts/<int:post_id>/gallery/<int:gallery_id>/",
        posts.PostGalleryDetailView.as_view(),
        name="post_gallery_detail",
    ),
    path("categories/", posts.CategoryListCreateView.as_view(), name="category_list"),
    path(
        "categories/<int:category_id>/",
        posts.CategoryDetailView.as_view(),
        name="category_detail",
    ),
    path("series/", posts.SeriesListCreateView.as_view(), name="series_list"),
    path(
        "series/<int:series_id>/",
        posts.SeriesDetailView.as_view(),
        name="series_detail",
    ),
    path(
        "publish/ready/", publish.PublishReadyPostsView.as_view(), name="publish_ready"
    ),
    path(
        "publish/telegram-preview/",
        publish.TelegramPreviewView.as_view(),
        name="telegram_preview",
    ),
    path(
        "publish/story-availability/",
        publish.StoryAvailabilityView.as_view(),
        name="story_availability",
    ),
    path("publish/", publish.PublishView.as_view(), name="publish"),
    path("media/upload/", media.MediaUploadView.as_view(), name="media_upload"),
    path("config/networks/", config.NetworkListView.as_view(), name="network_list"),
    path(
        "config/networks/<int:network_id>/",
        config.NetworkDetailView.as_view(),
        name="network_detail",
    ),
    path(
        "config/credentials/",
        config.CredentialListCreateView.as_view(),
        name="credential_list",
    ),
    path(
        "config/credentials/<int:credential_id>/",
        config.CredentialDetailView.as_view(),
        name="credential_detail",
    ),
    path(
        "config/telegram-settings/",
        config.TelegramSettingsView.as_view(),
        name="telegram_settings",
    ),
    path("audit/post-links/", config.PostLinkAuditView.as_view(), name="post_links"),
]
