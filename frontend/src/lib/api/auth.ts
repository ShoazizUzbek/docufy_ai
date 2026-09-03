import { apiRequest } from "./client";
import type { LoginResponse, User } from "./types";

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/auth/login/", {
    method: "POST",
    body: { email, password },
    skipAuth: true,
  });
}

export function fetchCurrentUser(): Promise<User> {
  return apiRequest<User>("/api/auth/me/");
}
