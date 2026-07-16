export type PostStatus = "draft" | "ready_to_publish" | "published";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  has_2fa: boolean;
}

export interface PostListItem {
  id: number;
  title: string;
  slug: string;
  status: PostStatus;
  author: { id: number; email: string; first_name: string; last_name: string };
  category: Category | null;
  tags: string[];
  updated: string;
  published: string | null;
  is_on_site: boolean;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface PostDetail extends PostListItem {
  uuid: string;
  body: string;
  short_description: string | null;
  cover_image: string | null;
  cover_image_url: string;
  cover_image_credits: string;
  cover_description: string;
  series: { id: number; name: string; slug: string }[];
  gallery_images: GalleryImage[];
  draft_preview_url: string;
  views: number;
  created: string;
}

export interface GalleryImage {
  id: number;
  gallery_key: number;
  image: string;
  image_url: string;
  caption: string;
  order: number;
}

export interface PublishResult {
  all_ok: boolean;
  post_id: number;
  status_updated: boolean;
  by_network: Record<
    string,
    {
      ok: boolean;
      message_url: string;
      error: string;
      detail: string;
    }
  >;
}

export interface TelegramPreviewCard {
  send_index: number;
  send_total: number;
  title: string;
  step_index: number;
  step_total: number;
  step_label: string;
  step_is_continuation: boolean;
  max_chars?: number;
  char_count: number;
  kind?: string;
  image_count?: number;
  limit_note?: string;
  cover_url?: string;
  thumb_row?: boolean;
  thumb_urls?: string[];
  has_text?: boolean;
  text?: string;
}

export interface TelegramPreviewPayload {
  is_series: boolean;
  step_count: number;
  send_count: number;
  has_subscription: boolean;
}

export interface TelegramPreviewResponse {
  ok: boolean;
  preview_cards: TelegramPreviewCard[];
  preview_payload?: TelegramPreviewPayload;
  telegram_layout_source?: string;
  telegram_owner_premium?: boolean | null;
}
