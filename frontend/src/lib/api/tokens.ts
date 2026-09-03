import type { AuthTokens } from "./types";

const ACCESS_KEY = "docufy_access_token";
const REFRESH_KEY = "docufy_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: AuthTokens): void {
  window.localStorage.setItem(ACCESS_KEY, tokens.access);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function setAccessToken(access: string): void {
  window.localStorage.setItem(ACCESS_KEY, access);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}
