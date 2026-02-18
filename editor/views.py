from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from taggit.models import Tag

from editor.forms import SearchForm
from editor.models import Category, Post


def post_list(request, tag_slug=None, category_slug=None):
    object_list = Post.objects.filter(status="published")
    tag = None
    category = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    if category_slug:
        category = Category.objects.filter(name=category_slug).first()
        object_list = object_list.filter(category=category)

        if not object_list:
            return render(
                request,
                "editor/post/list.html",
                {"page": None, "posts": None, "tag": tag},
            )

    paginator = Paginator(object_list, 12)
    page = request.GET.get("page")
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        "editor/post/list.html",
        {"page": page, "posts": posts, "tag": tag},
    )


def post_detail(request, slug):
    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    post.views += 1
    post.save(update_fields=["views"])

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

    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        Post.objects.filter(status="published")
        .filter(tags__in=post_tags_ids)
        .exclude(id=post.id)
    )
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-published"
    )[:3]

    newest_posts = (
        Post.objects.exclude(id=post.id)
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
