from django import template
from blog.models import Post

register = template.Library()


@register.inclusion_tag('blog/post/latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.objects.filter(status='published') \
                               .order_by('-published')[:count]
    return {'latest_posts': latest_posts}
