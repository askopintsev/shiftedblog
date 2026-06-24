# Shifted Blog Editor — Design System

Design tokens extracted from the public site ([`static_blog/css/blog.css`](../../static_blog/css/blog.css)).

## Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-text` | `#212529` | Headings, body, nav |
| `--color-text-muted` | `#6c757d` | Timestamps, help |
| `--color-text-secondary` | `#495057` | Stats, secondary labels |
| `--color-surface` | `#ffffff` | Cards, editor canvas |
| `--color-surface-muted` | `#f8f9fa` | Page background, zebra rows |
| `--color-border` | `#e2e6e9` | Dividers, inputs |
| `--color-accent` | `#0c63e4` | Primary buttons, active nav |
| `--color-tag-text` | `#2c5777` | Category/tag pills |
| `--color-tag-bg` | `#d1e5f1` | Category/tag pill background |
| `--color-warning` | `#ffc107` | SEO required field highlight |
| `--color-success` | `#198754` | Published status |
| `--color-draft` | `#6c757d` | Draft status |
| `--color-ready` | `#fd7e14` | Ready to publish status |

## Typography

- **Font:** Inter, system-ui fallback (400–700)
- **Body UI:** 14–16px
- **Editor canvas:** 18px (1.125rem), line-height 1.85, justified paragraphs
- **Headings in editor:** h3 1.75rem, h4 1.5rem, weight 600, letter-spacing -0.02em

## Spacing & radius

- Input radius: `8px`
- Card radius: `12px`
- Sidebar width: `240px` (collapsed `64px`)
- Editor max width: `700px` (matches public post detail)

## Components

- Status badges: draft (gray), ready_to_publish (amber), published (green)
- Primary button: accent background, white text
- Sidebar active item: accent left border + muted background

## Language

- UI copy: Russian
- URLs, slugs, code: Latin
