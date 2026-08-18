"""Render nginx/nginx.conf from nginx/nginx.conf.template and env."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse


def _split_hosts(raw: str) -> list[str]:
    hosts: list[str] = []
    for part in raw.split(","):
        host = part.strip().lower()
        if host:
            hosts.append(host)
    return hosts


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _join_names(names: list[str]) -> str:
    if not names:
        return ""
    return "\n                    ".join(names)


def _canonical_origin(site_url: str, domain: str) -> str:
    url = (site_url or "").strip().rstrip("/")
    if url:
        parsed = urlparse(url)
        if parsed.scheme and parsed.hostname:
            return f"{parsed.scheme}://{parsed.hostname.lower()}"
    return f"https://{domain}"


def _apex_and_www(domain: str, canonical_host: str) -> tuple[str, str]:
    apex = domain
    if apex.startswith("www."):
        apex = apex[4:]
    www = f"www.{apex}"
    if canonical_host.startswith("www."):
        apex = canonical_host[4:]
        www = canonical_host
    elif canonical_host and canonical_host != www:
        apex = canonical_host
        www = f"www.{canonical_host}"
    return apex, www


def _redirect_https_block(
    server_names: list[str],
    target_origin: str,
    ssl_certificate: str,
    ssl_certificate_key: str,
) -> str:
    names = _join_names(server_names)
    return f"""
    server {{
        listen 443 ssl;
        server_name {names};

        ssl_certificate {ssl_certificate};
        ssl_certificate_key {ssl_certificate_key};
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        location /.well-known/acme-challenge/ {{
            root /var/www/html;
            try_files $uri =404;
        }}

        location / {{
            return 301 {target_origin}$request_uri;
        }}
    }}
"""


def render(env: dict[str, str], template: str) -> str:
    domain = env.get("DOMAIN", "").strip()
    site_url = env.get("SITE_URL", "").strip()
    if not domain and site_url:
        parsed = urlparse(site_url)
        domain = (parsed.hostname or "").lower()
        if domain.startswith("www."):
            domain = domain[4:]
    if not domain:
        raise SystemExit("DOMAIN (or SITE_URL) is required.")

    editor_domain = env.get("EDITOR_DOMAIN", "").strip() or f"editor.{domain}"
    ssl_cert_name = env.get("SSL_CERT_NAME", "").strip() or domain
    extra_domains = _split_hosts(env.get("EXTRA_DOMAINS", ""))
    redirect_from = _split_hosts(env.get("REDIRECT_FROM_DOMAINS", ""))
    redirect_from_editor = _split_hosts(env.get("REDIRECT_FROM_EDITOR_DOMAINS", ""))
    server_ip = env.get("SERVER_IP", "").strip()

    canonical_origin = _canonical_origin(site_url, domain)
    canonical_host = urlparse(canonical_origin).hostname or domain
    apex, www_domain = _apex_and_www(domain, canonical_host)
    editor_origin = f"https://{editor_domain}"

    ssl_certificate = f"/etc/letsencrypt/live/{ssl_cert_name}/fullchain.pem"
    ssl_certificate_key = f"/etc/letsencrypt/live/{ssl_cert_name}/privkey.pem"

    redirect_hosts = set(redirect_from)
    redirect_editor_hosts = set(redirect_from_editor)
    if canonical_host == www_domain and apex != www_domain:
        redirect_hosts.add(apex)
    elif canonical_host == apex and www_domain != apex:
        redirect_hosts.add(www_domain)

    https_names: list[str] = [canonical_host]
    editor_names: list[str] = [editor_domain]
    http_names: list[str] = [apex, www_domain, editor_domain, canonical_host]

    for host in extra_domains:
        http_names.append(host)
        if host in redirect_hosts or host in redirect_editor_hosts:
            continue
        if host.startswith("editor."):
            editor_names.append(host)
        else:
            https_names.append(host)

    http_names.extend(redirect_from)
    http_names.extend(redirect_from_editor)
    if server_ip:
        http_names.append(server_ip)
        https_names.append(server_ip)

    https_names = [h for h in _unique(https_names) if h not in redirect_hosts]
    editor_names = [h for h in _unique(editor_names) if h not in redirect_editor_hosts]
    http_names = _unique(http_names)

    csp_hosts = {canonical_host, www_domain, apex}
    for host in extra_domains:
        if host.startswith("editor.") or host in redirect_hosts:
            continue
        csp_hosts.add(host)
    csp_origins = " ".join(f"https://{h}" for h in sorted(csp_hosts) if h)

    redirect_site_names = [h for h in _unique(list(redirect_hosts)) if h]
    redirect_editor_names = [h for h in _unique(list(redirect_editor_hosts)) if h]

    blocks = ""
    if redirect_site_names:
        blocks += _redirect_https_block(
            redirect_site_names,
            canonical_origin,
            ssl_certificate,
            ssl_certificate_key,
        )
    if redirect_editor_names:
        blocks += _redirect_https_block(
            redirect_editor_names,
            editor_origin,
            ssl_certificate,
            ssl_certificate_key,
        )

    replacements = {
        "__HTTP_SERVER_NAMES__": _join_names(http_names),
        "__HTTPS_SERVER_NAMES__": _join_names(https_names),
        "__EDITOR_SERVER_NAMES__": _join_names(editor_names),
        "__SSL_CERTIFICATE__": ssl_certificate,
        "__SSL_CERTIFICATE_KEY__": ssl_certificate_key,
        "__CSP_CONNECT_ORIGINS__": csp_origins,
        "__REDIRECT_HTTPS_BLOCKS__": blocks,
    }
    text = template
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {sys.argv[0]} TEMPLATE OUTPUT")
    template_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    text = render(dict(os.environ), template_path.read_text(encoding="utf-8"))
    output_path.write_text(text, encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
