"""DTOs for publish results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PublishResult:
    ok: bool
    url: str = ""
    error: str = ""
    detail: str = ""


@dataclass(slots=True)
class PublishJobResult:
    """Outcome of attempting all destinations in one job."""

    all_ok: bool
    post_id: int
    by_network: dict[str, PublishResult] = field(default_factory=dict)
    status_updated: bool = False
