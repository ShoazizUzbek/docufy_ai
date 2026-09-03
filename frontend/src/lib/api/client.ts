import { clearTokens, getAccessToken, getRefreshToken, setAccessToken } from "./tokens";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
  skipAuth?: boolean;
  /** Set internally to avoid infinite refresh loops. */
  _isRetry?: boolean;
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clearTokens();
    return null;
  }

  const data = (await response.json()) as { access: string };
  setAccessToken(data.access);
  return data.access;
}

function extractErrorMessage(data: unknown): string {
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    const firstKey = Object.keys(record)[0];
    if (firstKey) {
      const value = record[firstKey];
      if (Array.isArray(value) && typeof value[0] === "string") {
        return `${firstKey}: ${value[0]}`;
      }
    }
  }
  return "Something went wrong. Please try again.";
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isFormData = false, skipAuth = false, _isRetry = false } = options;

  const headers: Record<string, string> = {};
  if (!isFormData) headers["Content-Type"] = "application/json";

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !skipAuth && !_isRetry) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      return apiRequest<T>(path, { ...options, _isRetry: true });
    }
  }

  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      // no JSON body
    }
    throw new ApiError(response.status, extractErrorMessage(data), data);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
