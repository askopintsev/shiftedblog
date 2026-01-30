import datetime
import os

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_protect
from taggit.models import Tag

from blog.forms import SearchForm
from blog.models import Category, Person, Post


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
                "blog/post/list.html",
                {"page": None, "posts": None, "tag": tag},
            )

    paginator = Paginator(object_list, 12)  # 12 post on every page
    page = request.GET.get("page")
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page number is not an integer then set page #1
        posts = paginator.page(1)
    except EmptyPage:
        # If page number bigger than possible then set last page #
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        "blog/post/list.html",
        {"page": page, "posts": posts, "tag": tag},
    )


def post_detail(request, slug):
    post = get_object_or_404(
        Post,
        slug=slug,
        status="published",
    )

    # Increment views count
    post.views += 1
    post.save(update_fields=["views"])

    # Get series navigation (previous/next posts)
    previous_post = None
    next_post = None
    current_series = None

    # Get the first series this post belongs to (if any)
    post_series = post.post_series.filter(order_position__isnull=False).first()
    if post_series:
        current_series = post_series.series
        previous_post = post.get_previous_post_in_series(current_series)
        if previous_post and previous_post.status != "published":
            previous_post = None
        next_post = post.get_next_post_in_series(current_series)
        if next_post and next_post.status != "published":
            next_post = None

    # List of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        Post.objects.filter(status="published")
        .filter(tags__in=post_tags_ids)
        .exclude(id=post.id)
    )
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-published"
    )[:3]

    # List of newest posts
    newest_posts = (
        Post.objects.exclude(id=post.id)
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

            # Early return for empty queries
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

            # Limit query length to prevent abuse
            if len(query) > 200:
                query = query[:200]

            # Build search query and vector
            search_query = SearchQuery(query)
            search_vector = SearchVector("title", weight="A") + SearchVector(
                "body", weight="B"
            )

            # Optimized query: filter published, annotate rank, filter by min rank
            queryset = (
                Post.objects.filter(status="published")
                .annotate(rank=SearchRank(search_vector, search_query))
                .filter(rank__gte=0.3)
                .order_by("-rank", "-published")
            )

            # Add pagination (12 results per page, same as post_list)
            paginator = Paginator(queryset, 12)
            page = request.GET.get("page")
            try:
                results = paginator.page(page)
            except PageNotAnInteger:
                results = paginator.page(1)
            except EmptyPage:
                results = paginator.page(paginator.num_pages)

            # Build query string for pagination (preserve search query, exclude page)
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


def about(request):
    person = Person.objects.first()

    if not person:
        return render(
            request,
            "blog/about.html",
            {"person": None, "skills": None, "grouped_accounts": None},
        )

    skills = person.skill_set.all()
    accounts = person.account_set.all()
    grouped_accounts = {}
    for account in accounts:
        if account.group.name in grouped_accounts:
            grouped_accounts[account.group.name].append(account)
        else:
            grouped_accounts[account.group.name] = [account]

    return render(
        request,
        "blog/about.html",
        {"person": person, "skills": skills, "grouped_accounts": grouped_accounts},
    )


def custom_page_not_found_view(request, exception):
    return render(request, "blog/errors/404.html", {})


def custom_error_view(request, exception=None):
    return render(request, "blog/errors/500.html", {})


def custom_permission_denied_view(request, exception=None):
    return render(request, "blog/errors/403.html", {})


def custom_bad_request_view(request, exception=None):
    return render(request, "blog/errors/400.html", {})


@csrf_protect
def custom_image_upload(request):
    if request.method == "POST" and request.FILES.get("upload"):
        uploaded_file = request.FILES["upload"]
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"]
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in valid_extensions:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        date_path = datetime.datetime.now().strftime("%Y/%m/%d")
        filename = f"img/post/{date_path}/{uploaded_file.name}"
        file_path = default_storage.save(filename, ContentFile(uploaded_file.read()))

        url = f"{settings.MEDIA_URL}{file_path}"
        return JsonResponse(
            {
                "url": url,
                "uploaded": 1,
                "fileName": uploaded_file.name,
                "filePath": file_path,
            }
        )

    return JsonResponse({"error": "Invalid request"}, status=400)


def robots_txt(request):
    """Dynamic robots.txt view that uses settings for admin URL and site URL."""
    admin_url = getattr(settings, "ADMIN_URL", "mellon")
    site_url = getattr(settings, "SITE_URL", "http://localhost")

    # Build robots.txt content dynamically
    content = f"""User-agent: *
Allow: /
Disallow: /{admin_url}/
Disallow: /account/
Disallow: /drafts/

Sitemap: {site_url}/sitemap.xml
    """

    return HttpResponse(content, content_type="text/plain")
