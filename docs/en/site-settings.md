# Site settings

Русский: [../ru/site-settings.md](../ru/site-settings.md)

## What it is

A singleton row (`SiteSettings`) editable in:

- **Editor UI** → Settings → **Site** (`/config/site`)
- Django admin → **Core → Site settings**

Changes apply to the public site without rebuilding containers (cached briefly).

## Fields (v1)

| Group | Fields |
|-------|--------|
| Brand | `site_name`, `tagline`, `footer_text` |
| Social | `telegram_url`, `github_url`, `habr_url`, `twitter_site`, `contact_email` |
| Email (non-secret) | `default_from_email`, `admin_email`, `email_host`, `email_port`, `email_host_user`, `email_use_tls`, `email_use_ssl` |
| Toggles | `telegram_use_rich_messages`, `text_quality_checker_enabled` |

SMTP **password** remains `EMAIL_HOST_PASSWORD` in the secrets file.

## Future customization

Planned extensions (not in v1): logo upload, about-page content, analytics IDs, custom nav labels, theme accents. New fields will be added to the same model/admin.
