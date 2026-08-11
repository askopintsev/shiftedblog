# Site settings

English: [../en/site-settings.md](../en/site-settings.md)

## Что это

Одна запись (`SiteSettings`), редактируется в:

- **Editor UI** → Настройки → **Сайт** (`/config/site`)
- Django admin → **Core → Site settings**

Изменения видны на публичном сайте без пересборки контейнеров (короткий кэш).

## Поля (v1)

| Группа | Поля |
|--------|------|
| Бренд | `site_name`, `tagline`, `footer_text` |
| Соцсети | `telegram_url`, `github_url`, `habr_url`, `twitter_site`, `contact_email` |
| Email (несекретные) | `default_from_email`, `admin_email`, `email_host`, `email_port`, `email_host_user`, `email_use_tls`, `email_use_ssl` |
| Переключатели | `telegram_use_rich_messages`, `text_quality_checker_enabled` |

Пароль SMTP по-прежнему только в `EMAIL_HOST_PASSWORD`.

## Дальнейшая кастомизация

В планах (не в v1): логотип, текст «Обо мне», analytics ID, пункты меню, акценты темы — через расширение той же модели.
