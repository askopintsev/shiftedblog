/** Same-origin editor API path (nginx proxies this on editor.* hosts). */
export const DEFAULT_EDITOR_API_BASE = "/api/editor/v1";

/**
 * Resolve the editor API base URL.
 * On editor.* hosts always use same-origin /api/editor/v1.
 * Reject legacy misconfigurations such as bare SITE_URL in VITE_API_BASE.
 */
export function resolveApiBase(configured?: string): string {
  if (typeof window !== "undefined") {
    const { hostname } = window.location;
    if (hostname.startsWith("editor.")) {
      return DEFAULT_EDITOR_API_BASE;
    }
  }

  const trimmed = configured?.trim();
  if (!trimmed) {
    return DEFAULT_EDITOR_API_BASE;
  }

  const normalized = trimmed.replace(/\/+$/, "");
  if (/^https?:\/\//i.test(normalized) && !normalized.includes("/api/editor/")) {
    return DEFAULT_EDITOR_API_BASE;
  }

  return normalized;
}
