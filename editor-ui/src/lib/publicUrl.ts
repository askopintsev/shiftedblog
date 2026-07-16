const PUBLIC_SITE_BASE =
  import.meta.env.VITE_PUBLIC_SITE_BASE ??
  (import.meta.env.DEV ? "http://localhost:8888" : "");

export function publicUrl(url: string | null | undefined): string {
  if (!url) return "";

  try {
    const parsed = new URL(url, window.location.origin);
    if (!PUBLIC_SITE_BASE) {
      return parsed.href;
    }
    const base = new URL(PUBLIC_SITE_BASE);
    return `${base.origin}${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return url;
  }
}
