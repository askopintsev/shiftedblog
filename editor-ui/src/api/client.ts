const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/editor/v1";

let csrfToken = "";

function readCsrfFromCookie(): string {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function resolveCsrfToken(): string {
  return csrfToken || readCsrfFromCookie();
}

export function getCsrfToken(): string {
  return resolveCsrfToken();
}

export function resetCsrfToken(): void {
  csrfToken = "";
}

export async function fetchCsrf(): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include" });
  const data = (await res.json()) as { csrfToken: string };
  csrfToken = data.csrfToken || readCsrfFromCookie();
  return csrfToken;
}

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function request(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  if (!resolveCsrfToken() && !path.includes("/auth/csrf")) {
    await fetchCsrf();
  }
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const method = options.method ?? "GET";
  const csrf = resolveCsrfToken();
  if (csrf && method !== "GET") {
    headers.set("X-CSRFToken", csrf);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
  if (res.status === 403 && method !== "GET" && !path.includes("/auth/csrf")) {
    await fetchCsrf();
    const retryHeaders = new Headers(headers);
    const retryCsrf = resolveCsrfToken();
    if (retryCsrf) {
      retryHeaders.set("X-CSRFToken", retryCsrf);
    }
    return fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers: retryHeaders,
    });
  }
  return res;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await request(path, options);
  if (res.status === 204) {
    return undefined as T;
  }
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      (payload as { error?: string }).error ?? res.statusText,
      res.status,
      payload,
    );
  }
  return payload as T;
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  method: "POST" | "PATCH" = "POST",
): Promise<T> {
  if (!resolveCsrfToken()) {
    await fetchCsrf();
  }
  const res = await request(path, { method, body: formData });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      (payload as { error?: string }).error ?? res.statusText,
      res.status,
      payload,
    );
  }
  return payload as T;
}

export { API_BASE };
