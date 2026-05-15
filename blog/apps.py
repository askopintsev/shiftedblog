from typing import ClassVar

from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field: ClassVar[str] = "django.db.models.BigAutoField"
    name: ClassVar[str] = "blog"
    verbose_name: ClassVar[str] = "Blog"

    def ready(self) -> None:
        import blog.signals  # noqa: F401
