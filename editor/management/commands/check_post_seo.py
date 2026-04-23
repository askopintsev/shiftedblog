"""Validate published post HTML: canonical link, robots meta, JSON-LD schema."""

from __future__ import annotations

# pyright: reportAttributeAccessIssue=false
import json
import re
from contextlib import AbstractContextManager
from typing import Any, Protocol, cast
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.http import HttpResponse
from django.test import Client
from django.test.utils import override_settings

from editor.models import Post

_LINK_TAG_RE = re.compile(r"<link\s+([^>]+)>", re.IGNORECASE)
_META_TAG_RE = re.compile(r"<meta\s+([^>]+)>", re.IGNORECASE)
_ATTR_RE = re.compile(r"(\w+)\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_LD_JSON_SCRIPT_RE = re.compile(
    r'<script\s+type\s*=\s*["\']application/ld\+json["\']\s*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _attrs_dict(attr_string: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2) for m in _ATTR_RE.finditer(attr_string)}


def _find_canonical_hrefs(html: str) -> list[str]:
    hrefs: list[str] = []
    for m in _LINK_TAG_RE.finditer(html):
        attrs = _attrs_dict(m.group(1))
        rel = (attrs.get("rel") or "").lower()
        if rel == "canonical" and "href" in attrs:
            hrefs.append(attrs["href"].strip())
    return hrefs


def _find_robots_meta_contents(html: str) -> list[str]:
    contents: list[str] = []
    for m in _META_TAG_RE.finditer(html):
        attrs = _attrs_dict(m.group(1))
        name = (attrs.get("name") or "").lower()
        if name == "robots" and "content" in attrs:
            contents.append(attrs["content"].strip().lower())
    return contents


def _parse_ld_json_blocks(html: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for m in _LD_JSON_SCRIPT_RE.finditer(html):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            blocks.append(data)
        elif isinstance(data, list):
            blocks.extend(item for item in data if isinstance(item, dict))
    return blocks


def _norm_url(url: str) -> str:
    return url.strip().rstrip("/")


def _expected_canonical(path: str) -> str:
    base = settings.SITE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


class _CommandStyle(Protocol):
    """django.core.management.color.Style (stubs omit WARNING / ERROR / SUCCESS)."""

    def WARNING(self, text: str = "") -> str: ...  # noqa: N802
    def ERROR(self, text: str = "") -> str: ...  # noqa: N802
    def SUCCESS(self, text: str = "") -> str: ...  # noqa: N802


class Command(BaseCommand):
    help = (
        "Fetch each published post detail page and check canonical URL, "
        "robots meta, and BlogPosting / BreadcrumbList JSON-LD (for CI)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            type=str,
            default="",
            help="Only check the post with this slug.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max posts to check (0 = all).",
        )

    def handle(self, *args, **options):
        slug_filter: str = options["slug"]
        limit: int = options["limit"]

        site = urlparse(settings.SITE_URL)
        if not site.scheme or not site.netloc:
            raise CommandError(f"Invalid SITE_URL: {settings.SITE_URL!r}")

        host = site.netloc
        secure = site.scheme == "https"

        extra_hosts = {h.strip() for h in settings.ALLOWED_HOSTS if h.strip()}
        extra_hosts.add(host)
        extra_hosts_list = sorted(extra_hosts) if "*" not in extra_hosts else ["*"]

        qs = Post.objects.filter(status="published").order_by("slug")
        if slug_filter:
            qs = qs.filter(slug=slug_filter)
        if limit > 0:
            qs = qs[:limit]

        posts = list(qs)
        style = cast(_CommandStyle, self.style)
        if not posts:
            self.stdout.write(style.WARNING("No published posts to check."))
            return

        errors: list[str] = []

        with override_settings(ALLOWED_HOSTS=extra_hosts_list):
            client = Client(HTTP_HOST=host)

            for post in posts:
                path = post.get_absolute_url()
                expected = _expected_canonical(path)

                with cast(AbstractContextManager[Any], transaction.atomic()):
                    response = cast(
                        HttpResponse,
                        client.get(path, secure=secure),
                    )
                    transaction.set_rollback(True)

                if response.status_code != 200:
                    errors.append(
                        f"{post.slug!r}: HTTP {response.status_code} (expected 200)"
                    )
                    continue

                content = response.content.decode(response.charset or "utf-8")

                canon_hrefs = _find_canonical_hrefs(content)
                if len(canon_hrefs) != 1:
                    errors.append(
                        f"{post.slug!r}: expected exactly one canonical <link>, "
                        f"found {len(canon_hrefs)}"
                    )
                elif _norm_url(canon_hrefs[0]) != _norm_url(expected):
                    errors.append(
                        f"{post.slug!r}: canonical href {canon_hrefs[0]!r} != "
                        f"expected {expected!r}"
                    )

                robots_vals = _find_robots_meta_contents(content)
                for rv in robots_vals:
                    if "noindex" in rv or "nofollow" in rv:
                        errors.append(
                            f"{post.slug!r}: published page must not use "
                            f'noindex/nofollow in <meta name="robots"> '
                            f"(got content={rv!r})"
                        )

                ld_blocks = _parse_ld_json_blocks(content)
                blog: dict[str, Any] | None = None
                crumbs: dict[str, Any] | None = None
                for block in ld_blocks:
                    t = block.get("@type")
                    types = t if isinstance(t, list) else ([t] if t else [])
                    if "BlogPosting" in types:
                        blog = block
                    if "BreadcrumbList" in types:
                        crumbs = block

                if blog is None:
                    errors.append(
                        f"{post.slug!r}: no JSON-LD block with @type BlogPosting"
                    )
                else:
                    headline = blog.get("headline")
                    if not headline or not str(headline).strip():
                        errors.append(
                            f"{post.slug!r}: BlogPosting missing non-empty headline"
                        )
                    mep = blog.get("mainEntityOfPage")
                    if not isinstance(mep, dict):
                        errors.append(
                            f"{post.slug!r}: BlogPosting.mainEntityOfPage must be "
                            f"an object"
                        )
                    else:
                        mid = mep.get("@id")
                        if mid is None:
                            errors.append(
                                f"{post.slug!r}: BlogPosting.mainEntityOfPage "
                                f"missing @id"
                            )
                        elif _norm_url(str(mid)) != _norm_url(expected):
                            errors.append(
                                f"{post.slug!r}: mainEntityOfPage.@id {mid!r} != "
                                f"expected canonical {expected!r}"
                            )

                if crumbs is None:
                    errors.append(
                        f"{post.slug!r}: no JSON-LD block with @type BreadcrumbList"
                    )
                else:
                    items = crumbs.get("itemListElement")
                    if not isinstance(items, list) or not items:
                        errors.append(
                            f"{post.slug!r}: BreadcrumbList.itemListElement "
                            f"must be a non-empty list"
                        )
                    else:
                        last = items[-1]
                        if not isinstance(last, dict):
                            errors.append(
                                f"{post.slug!r}: last breadcrumb item must be an object"
                            )
                        else:
                            last_item = last.get("item")
                            if last_item is None:
                                errors.append(
                                    f"{post.slug!r}: last breadcrumb missing item URL"
                                )
                            elif _norm_url(str(last_item)) != _norm_url(expected):
                                errors.append(
                                    f"{post.slug!r}: last breadcrumb item "
                                    f"{last_item!r} != expected {expected!r}"
                                )

        if errors:
            self.stdout.write(style.ERROR(f"Failed ({len(errors)} issue(s)):"))
            for msg in errors:
                self.stdout.write(style.ERROR(f"  - {msg}"))
            raise CommandError(f"SEO meta check failed with {len(errors)} error(s).")

        self.stdout.write(
            style.SUCCESS(f"OK — checked {len(posts)} published post(s).")
        )
