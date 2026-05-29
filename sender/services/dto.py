"""DTOs for publish results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PublishResult:
    ok: bool
    message_url: str = ""
    message_id: int | None = None
    story_id: int | None = None
    story_url: str = ""
    error: str = ""
    detail: str = ""

    @property
    def url(self) -> str:
        """Backward-compatible alias for ``message_url``."""
        return self.message_url


@dataclass(slots=True)
class StoryAvailabilityDTO:
    available: bool
    reason: str = ""
    bot_can_post_stories: bool | None = None
    free_story_slots: int | None = None


@dataclass(slots=True)
class PublishJobResult:
    """Outcome of attempting all destinations in one job."""

    all_ok: bool
    post_id: int
    by_network: dict[str, PublishResult] = field(default_factory=dict)
    status_updated: bool = False
