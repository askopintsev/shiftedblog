const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/editor/v1";

let csrfToken = "";

export function getCsrfToken(): string {
  return csrfToken;
}

export function resetCsrfToken(): void {
  csrfToken = "";
}

export async function fetchCsrf(): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include" });
  const data = (await res.json()) as { csrfToken: string };
  csrfToken = data.csrfToken;
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

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!csrfToken && !path.includes("/auth/csrf")) {
    await fetchCsrf();
  }
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (csrfToken && options.method && options.method !== "GET") {
    headers.set("X-CSRFToken", csrfToken);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
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
  if (!csrfToken) {
    await fetchCsrf();
  }
  const headers = new Headers();
  if (csrfToken) {
    headers.set("X-CSRFToken", csrfToken);
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body: formData,
    credentials: "include",
    headers,
  });
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
