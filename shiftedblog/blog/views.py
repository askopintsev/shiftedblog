from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from blog.forms import SearchForm
from blog.models import Person, Post, Category
from taggit.models import Tag


def post_list(request, tag_slug=None, category_slug=None):
    object_list = Post.objects.filter(status='published')
    tag = None
    category = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    if category_slug:
        category = get_object_or_404(Category, name=category_slug)
        object_list = object_list.filter(category=category)

    paginator = Paginator(object_list, 12)  # 12 post on every page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page number is not an integer then set page #1
        posts = paginator.page(1)
    except EmptyPage:
        # If page number bigger than possible then set last page #
        posts = paginator.page(paginator.num_pages)
    return render(request,
                  'blog/post/list.html',
                  {'page': page,
                   'posts': posts,
                   'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             slug=post,
                             status='published',
                             published__year=year,
                             published__month=month,
                             published__day=day)

    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.objects.filter(status='published')\
                                .filter(tags__in=post_tags_ids) \
                                .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')) \
                                 .order_by('-same_tags', '-published')[:3]

    # List of newest posts
    newest_posts = Post.objects.exclude(id=post.id)\
                               .exclude(id__in=similar_posts)\
                               .order_by('-published')[:5-len(similar_posts)]

    return render(request,
                  'blog/post/detail.html',
                  {'post': post,
                   'similar_posts': similar_posts,
                   'newest_posts': newest_posts
                   })


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            results = Post.objects.annotate(rank=SearchRank(search_vector, search_query))\
                                  .filter(rank__gte=0.3)\
                                  .order_by('-rank')

    return render(request,
                  'blog/post/search.html',
                  {'form': form,
                   'query': query,
                   'results': results})


def about(request):
    person = Person.objects.get(id=1)
    skills = person.skill_set.all()
    accounts = person.account_set.all()
    grouped_accounts = {}
    for account in accounts:
        if account.group.name in grouped_accounts:
            grouped_accounts[account.group.name].append(account)
        else:
            grouped_accounts[account.group.name] = [account]

    return render(request,
                  'blog/about.html',
                  {'person': person,
                   'skills': skills,
                   'grouped_accounts': grouped_accounts})


def custom_page_not_found_view(request, exception):
    return render(request, "blog/errors/404.html", {})


def custom_error_view(request, exception=None):
    return render(request, "blog/errors/500.html", {})


def custom_permission_denied_view(request, exception=None):
    return render(request, "blog/errors/403.html", {})


def custom_bad_request_view(request, exception=None):
    return render(request, "blog/errors/400.html", {})
