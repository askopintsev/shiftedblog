/** Same-origin ``/media/...`` path for dev proxy and production nginx. */
export function mediaUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/")) return url;
  try {
    const parsed = new URL(url);
    return parsed.pathname + parsed.search;
  } catch {
    return url;
  }
}
