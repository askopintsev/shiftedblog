from typing import ClassVar

from django.apps import AppConfig


class EditorConfig(AppConfig):
    default_auto_field: ClassVar[str] = "django.db.models.BigAutoField"
    name: ClassVar[str] = "editor"
    verbose_name: ClassVar[str] = "Editor"

    def ready(self) -> None:
        import editor.signals  # noqa: F401
