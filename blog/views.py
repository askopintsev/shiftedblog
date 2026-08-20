# pyright: reportAttributeAccessIssue=false
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch
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
from blog.querysets import feed_posts_queryset, public_posts_queryset
from blog.related_posts import series_navigation, similar_and_newest_posts
from blog.tag_helpers import resolve_tag_for_list
from editor.forms import SearchForm
from editor.image_upload import (
    ensure_post_share_image,
    social_share_image_size,
)
from editor.models import Category, PostSlugRedirect
from sender.models import PostLink
from sender.services.url_helpers import (
    post_og_image_absolute_url,
    post_share_image_media_url,
)


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

    current_series, previous_post, next_post = series_navigation(post)
    excluded_series_post_ids = [
        series_post.id
        for series_post in (previous_post, next_post)
        if series_post is not None
    ]
    similar_posts, newest_posts = similar_and_newest_posts(
        post,
        excluded_ids=excluded_series_post_ids,
    )

    if post.cover_image and post.cover_image.name:
        ensure_post_share_image(post)

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


def post_og_image(request, slug: str) -> HttpResponse:
    """Legacy URL: generate share JPEG if needed, then redirect to ``/media/``."""
    post = public_posts_queryset().filter(slug=slug).first()
    if post is None or not post.cover_image or not post.cover_image.name:
        raise Http404("No share image for this post.")

    if not ensure_post_share_image(post):
        raise Http404("Cover image is not readable.")

    media_url = post_share_image_media_url(post)
    if media_url is None:
        raise Http404("Share image unavailable.")

    return HttpResponsePermanentRedirect(request.build_absolute_uri(media_url))


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
        feed_posts_queryset()
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
