# pyright: reportAttributeAccessIssue=false
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Prefetch
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponsePermanentRedirect,
)
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from taggit.models import Tag

from blog.category_helpers import resolve_category_for_list
from blog.querysets import public_posts_queryset
from blog.tag_helpers import resolve_tag_for_list
from editor.forms import SearchForm
from editor.image_upload import (
    build_share_jpeg_from_cover_bytes,
    read_cover_bytes,
    share_jpeg_has_social_dimensions,
    social_share_image_size,
    social_share_storage_name,
)
from editor.models import Category, PostSlugRedirect
from sender.models import PostLink
from sender.services.url_helpers import post_og_image_absolute_url


def _public_page_cache(key_prefix: str):
    timeout = getattr(settings, "POST_PAGE_CACHE_TIMEOUT", 0)
    if timeout <= 0 or settings.DEBUG or not getattr(settings, "IS_PRODUCTION", True):

        def _noop(view):
            return view

        return _noop
    return cache_page(timeout, key_prefix=key_prefix)


def _label_for_category_slug(category_slug: str | None) -> str:
    if not category_slug:
        return "Рубрика"
    parts = category_slug.replace("_", "-").split("-")
    pretty = " ".join(p.capitalize() for p in parts if p)
    return pretty or category_slug


def _post_list_seo(
    request: HttpRequest,
    *,
    tag: Tag | None,
    category: Category | None,
    category_slug: str | None,
    tag_slug: str | None,
    posts_page,
    list_empty: bool,
) -> dict[str, str | None]:
    site = settings.SITE_URL.rstrip("/")
    site_name = "Shifted Stuff"

    if posts_page is not None:
        page_num = posts_page.number
        total_pages = posts_page.paginator.num_pages
    else:
        page_num = 1
        total_pages = 1

    path = request.path
    if page_num <= 1:
        canonical_url = f"{site}{path}"
    else:
        canonical_url = f"{site}{path}?page={page_num}"

    list_heading: str | None = None

    if category is not None:
        display_name = (category.name or "").strip() or _label_for_category_slug(
            category_slug
        )
        list_heading = display_name
        title_base = f"{display_name} — {site_name}"
        desc_base = f"Статьи и заметки в категории «{display_name}»."
    elif category_slug:
        display_name = _label_for_category_slug(category_slug)
        list_heading = display_name
        title_base = f"{display_name} — {site_name}"
        desc_base = f"Публикации в разделе «{display_name}»."
    elif tag is not None:
        title_base = f"#{tag.name} — {site_name}"
        desc_base = f"Все публикации с тегом #{tag.name}."
    elif tag_slug:
        title_base = f"Тег — {site_name}"
        desc_base = "Публикации по выбранному тегу."
    else:
        title_base = site_name
        desc_base = "Блог Shifted Stuff: публикации, заметки и статьи."

    if page_num > 1:
        title = f"{title_base} — стр. {page_num}"
        description = f"{desc_base} Страница {page_num} из {total_pages}."
    else:
        title = title_base
        description = desc_base

    if list_empty:
        description = f"{description} Пока нет опубликованных материалов."

    return {
        "canonical_url": canonical_url,
        "title": title,
        "description": description,
        "list_heading": list_heading,
    }


@vary_on_cookie
@_public_page_cache("blog.post_list")
def post_list(request, tag_slug=None, category_slug=None):
    object_list = public_posts_queryset()
    tag = None
    category = None

    if tag_slug:
        tag, redirect = resolve_tag_for_list(tag_slug)
        if redirect is not None:
            return redirect
        if tag is None:
            raise Http404("Tag not found")
        object_list = object_list.filter(tags__in=[tag])

    if category_slug:
        category, redirect = resolve_category_for_list(category_slug)
        if redirect is not None:
            return redirect
        if category is not None:
            object_list = object_list.filter(category=category)
        else:
            object_list = object_list.none()

    if not object_list:
        list_seo = _post_list_seo(
            request,
            tag=tag,
            category=category,
            category_slug=category_slug,
            tag_slug=tag_slug,
            posts_page=None,
            list_empty=True,
        )
        return render(
            request,
            "blog/post/list.html",
            {
                "page": None,
                "posts": None,
                "tag": tag,
                "category": category,
                "list_seo": list_seo,
            },
        )

    paginator = Paginator(object_list, 12)
    page = request.GET.get("page")
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    list_seo = _post_list_seo(
        request,
        tag=tag,
        category=category,
        category_slug=category_slug,
        tag_slug=tag_slug,
        posts_page=posts,
        list_empty=False,
    )
    return render(
        request,
        "blog/post/list.html",
        {
            "page": page,
            "posts": posts,
            "tag": tag,
            "category": category,
            "list_seo": list_seo,
        },
    )


@vary_on_cookie
@_public_page_cache("blog.post_detail")
def post_detail(request, slug):
    post = (
        public_posts_queryset()
        .prefetch_related("gallery_images")
        .filter(slug=slug)
        .first()
    )
    if post is None:
        redirect_row = (
            PostSlugRedirect.objects.select_related("post")
            .filter(old_slug=slug)
            .first()
        )
        if (
            redirect_row
            and redirect_row.post.status == "published"
            and hasattr(redirect_row.post, "site_publication")
        ):
            return HttpResponsePermanentRedirect(redirect_row.post.get_absolute_url())
        raise Http404("No published post matches this URL.")

    previous_post = None
    next_post = None
    current_series = None

    post_series = post.post_series.filter(order_position__isnull=False).first()
    if post_series:
        current_series = post_series.series
        previous_post = post.get_previous_post_in_series(current_series)
        if previous_post and (
            previous_post.status != "published"
            or not hasattr(previous_post, "site_publication")
        ):
            previous_post = None
        next_post = post.get_next_post_in_series(current_series)
        if next_post and (
            next_post.status != "published"
            or not hasattr(next_post, "site_publication")
        ):
            next_post = None

    excluded_series_post_ids = [
        series_post.id
        for series_post in (previous_post, next_post)
        if series_post is not None
    ]

    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        public_posts_queryset().filter(tags__in=post_tags_ids).exclude(id=post.id)
    )
    if excluded_series_post_ids:
        similar_posts = similar_posts.exclude(id__in=excluded_series_post_ids)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-published"
    )[:3]

    newest_posts = (
        public_posts_queryset()
        .exclude(id=post.id)
        .exclude(id__in=excluded_series_post_ids)
        .exclude(id__in=similar_posts)
        .order_by("-published")[: 5 - len(similar_posts)]
    )

    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post,
            "similar_posts": similar_posts,
            "newest_posts": newest_posts,
            "previous_post": previous_post,
            "next_post": next_post,
            "current_series": current_series,
            "post_og_image_url": post_og_image_absolute_url(post, request),
            "post_og_image_width": social_share_image_size()[0],
            "post_og_image_height": social_share_image_size()[1],
        },
    )


@_public_page_cache("blog.post_og_image")
def post_og_image(request, slug: str) -> HttpResponse:
    """Serve JPEG cover art for link-preview crawlers (Telegram, X/Twitter)."""
    post = public_posts_queryset().filter(slug=slug).first()
    if post is None or not post.cover_image or not post.cover_image.name:
        raise Http404("No share image for this post.")

    cover_name = post.cover_image.name
    share_name = social_share_storage_name(cover_name)
    if default_storage.exists(share_name):
        with default_storage.open(share_name, "rb") as share_file:
            data = share_file.read()
        if share_jpeg_has_social_dimensions(data):
            return _jpeg_image_response(data)

    try:
        raw = read_cover_bytes(post.cover_image)
        data = build_share_jpeg_from_cover_bytes(raw)
    except (OSError, ValueError) as exc:
        raise Http404("Cover image is not readable.") from exc

    default_storage.save(share_name, ContentFile(data))
    return _jpeg_image_response(data)


def _jpeg_image_response(data: bytes) -> HttpResponse:
    response = HttpResponse(data, content_type="image/jpeg")
    response["Cache-Control"] = "public, max-age=604800, immutable"
    return response


def post_search(request):
    form = SearchForm()
    query = None
    results = None
    query_string = ""

    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"].strip()

            if not query:
                return render(
                    request,
                    "blog/post/search.html",
                    {
                        "form": form,
                        "query": None,
                        "results": None,
                        "query_string": "",
                    },
                )

            if len(query) > 200:
                query = query[:200]

            search_query = SearchQuery(query)
            search_vector = SearchVector("title", weight="A") + SearchVector(
                "body", weight="B"
            )

            queryset = (
                public_posts_queryset()
                .annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gte=0.3)
                .order_by("-rank", "-published")
            )

            paginator = Paginator(queryset, 12)
            page = request.GET.get("page")
            try:
                results = paginator.page(page)
            except PageNotAnInteger:
                results = paginator.page(1)
            except EmptyPage:
                results = paginator.page(paginator.num_pages)

            query_params = request.GET.copy()
            if "page" in query_params:
                del query_params["page"]
            query_string = query_params.urlencode()

    return render(
        request,
        "blog/post/search.html",
        {
            "form": form,
            "query": query,
            "results": results,
            "query_string": query_string,
        },
    )


@login_required
def post_feed_lenta(request: HttpRequest):
    """Authenticated feed: all site-published posts with outbound PostLink buttons."""
    queryset = (
        public_posts_queryset()
        .select_related("category", "author")
        .prefetch_related(
            Prefetch(
                "sender_links",
                queryset=PostLink.objects.select_related("network").order_by(
                    "network__slug",
                ),
            ),
            "tags",
        )
        .order_by("-published")
    )
    paginator = Paginator(queryset, 12)
    page = request.GET.get("page") or 1
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(
        request,
        "blog/post/feed_lenta.html",
        {"posts": posts},
    )


def html_sitemap(request):
    posts = list(
        public_posts_queryset()
        .select_related("category")
        .prefetch_related("tags")
        .order_by("-published")
    )

    categories = (
        Category.objects.filter(
            blog_category__status="published",
            blog_category__site_publication__isnull=False,
        )
        .exclude(name__isnull=True)
        .exclude(name__exact="")
        .distinct()
        .order_by("name")
    )

    tags_by_slug = {}
    for post in posts:
        for tag in post.tags.all():
            tags_by_slug[tag.slug] = tag
    tags = sorted(tags_by_slug.values(), key=lambda tag: tag.name.lower())

    return render(
        request,
        "blog/post/sitemap.html",
        {
            "posts": posts,
            "categories": categories,
            "tags": tags,
        },
    )
