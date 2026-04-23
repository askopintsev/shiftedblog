# pyright: reportAttributeAccessIssue=false
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page
from taggit.models import Tag

from editor.forms import SearchForm
from editor.models import Category, Post, PostSlugRedirect


def _public_page_cache(key_prefix: str):
    timeout = getattr(settings, "POST_PAGE_CACHE_TIMEOUT", 0)
    if timeout <= 0:

        def _noop(view):
            return view

        return _noop
    return cache_page(timeout, key_prefix=key_prefix)


def _label_for_category_slug(category_slug: str | None) -> str:
    if not category_slug:
        return "Рубрика"
    labels = getattr(settings, "CATEGORY_URL_SLUG_LABELS", None) or {}
    key = category_slug.lower()
    if key in labels:
        return labels[key]
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
    """Canonical URL, document title, and meta description for list views."""
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
        desc_base = f"Все публикации с тегом #{tag.name}."  # noqa: RUF001
    elif tag_slug:
        title_base = f"Тег — {site_name}"  # noqa: RUF001
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


@_public_page_cache("editor.post_list")
def post_list(request, tag_slug=None, category_slug=None):
    object_list = Post.objects.filter(status="published")
    tag = None
    category = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    if category_slug:
        category = Category.objects.filter(name=category_slug).first()
        if category is None:
            category = next(
                (
                    c
                    for c in Category.objects.all()
                    if c.list_url_segment() == category_slug
                ),
                None,
            )
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
            "editor/post/list.html",
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
        "editor/post/list.html",
        {
            "page": page,
            "posts": posts,
            "tag": tag,
            "category": category,
            "list_seo": list_seo,
        },
    )


@_public_page_cache("editor.post_detail")
def post_detail(request, slug):
    post = (
        Post.objects.prefetch_related("gallery_images")
        .filter(slug=slug, status="published")
        .first()
    )
    if post is None:
        redirect_row = (
            PostSlugRedirect.objects.select_related("post")
            .filter(old_slug=slug)
            .first()
        )
        if redirect_row and redirect_row.post.status == "published":
            return HttpResponsePermanentRedirect(redirect_row.post.get_absolute_url())
        raise Http404("No published post matches this URL.")

    previous_post = None
    next_post = None
    current_series = None

    post_series = post.post_series.filter(order_position__isnull=False).first()
    if post_series:
        current_series = post_series.series
        previous_post = post.get_previous_post_in_series(current_series)
        if previous_post and previous_post.status != "published":
            previous_post = None
        next_post = post.get_next_post_in_series(current_series)
        if next_post and next_post.status != "published":
            next_post = None

    excluded_series_post_ids = [
        series_post.id
        for series_post in (previous_post, next_post)
        if series_post is not None
    ]

    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        Post.objects.filter(status="published")
        .filter(tags__in=post_tags_ids)
        .exclude(id=post.id)
    )
    if excluded_series_post_ids:
        similar_posts = similar_posts.exclude(id__in=excluded_series_post_ids)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-published"
    )[:3]

    newest_posts = (
        Post.objects.filter(status="published")
        .exclude(id=post.id)
        .exclude(id__in=excluded_series_post_ids)
        .exclude(id__in=similar_posts)
        .order_by("-published")[: 5 - len(similar_posts)]
    )

    return render(
        request,
        "editor/post/detail.html",
        {
            "post": post,
            "similar_posts": similar_posts,
            "newest_posts": newest_posts,
            "previous_post": previous_post,
            "next_post": next_post,
            "current_series": current_series,
        },
    )


def post_detail_by_uuid(request, uuid):
    """View a post by secret UUID (any status, including draft)."""
    post = get_object_or_404(
        Post.objects.prefetch_related("gallery_images"),
        uuid=uuid,
    )
    # Don't increment views for draft preview

    previous_post = None
    next_post = None
    current_series = None
    post_series = post.post_series.filter(order_position__isnull=False).first()
    if post_series:
        current_series = post_series.series
        previous_post = post.get_previous_post_in_series(current_series)
        if previous_post and previous_post.status != "published":
            previous_post = None
        next_post = post.get_next_post_in_series(current_series)
        if next_post and next_post.status != "published":
            next_post = None

    excluded_series_post_ids = [
        series_post.id
        for series_post in (previous_post, next_post)
        if series_post is not None
    ]

    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        Post.objects.filter(status="published")
        .filter(tags__in=post_tags_ids)
        .exclude(id=post.id)
    )
    if excluded_series_post_ids:
        similar_posts = similar_posts.exclude(id__in=excluded_series_post_ids)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-published"
    )[:3]

    newest_posts = (
        Post.objects.filter(status="published")
        .exclude(id=post.id)
        .exclude(id__in=excluded_series_post_ids)
        .exclude(id__in=similar_posts)
        .order_by("-published")[: 5 - len(similar_posts)]
    )

    response = render(
        request,
        "editor/post/detail.html",
        {
            "post": post,
            "similar_posts": similar_posts,
            "newest_posts": newest_posts,
            "previous_post": previous_post,
            "next_post": next_post,
            "current_series": current_series,
            "is_draft_preview": post.status != "published",
        },
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
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
                    "editor/post/search.html",
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
                Post.objects.filter(status="published")
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
        "editor/post/search.html",
        {
            "form": form,
            "query": query,
            "results": results,
            "query_string": query_string,
        },
    )


def html_sitemap(request):
    posts = list(
        Post.objects.filter(status="published")
        .select_related("category")
        .prefetch_related("tags")
        .order_by("-published")
    )

    categories = (
        Category.objects.filter(blog_category__status="published")
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
        "editor/post/sitemap.html",
        {
            "posts": posts,
            "categories": categories,
            "tags": tags,
        },
    )
