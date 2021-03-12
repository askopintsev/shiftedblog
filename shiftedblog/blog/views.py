from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from blog.forms import SearchForm
from blog.models import Post, Category
from taggit.models import Tag


# class PostListView(ListView):
#     queryset = Post.objects.filter(status='published')
#     context_object_name = 'posts'
#     paginate_by = 30
#     template_name = 'blog/post/list.html'


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

    paginator = Paginator(object_list, 10)  # 10 post on every page
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

    return render(request,
                  'blog/post/detail.html',
                  {'post': post,
                   'similar_posts': similar_posts
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
    return render(request,
                  'blog/about.html')
