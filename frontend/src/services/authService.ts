import {
  request,
  getStoredToken,
  setStoredToken,
} from "./apiClient";
import type { AuthUser, Role } from "@/data/mock/mockData";

export interface LoginResponsePayload {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    name: string;
    email: string;
    role: Role;
    section?: string;
    year?: string;
    roll_number?: string;
  };
}

function toAuthUser(user: LoginResponsePayload["user"]): AuthUser {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    role: user.role,
    ...(user.section !== undefined ? { section: user.section } : {}),
    ...(user.year !== undefined ? { year: user.year } : {}),
  };
}

export async function login(
  email: string,
  password: string,
  portal: "ADMIN" | "CRLR" | "MENTOR"
): Promise<AuthUser> {
  const data = await request<LoginResponsePayload>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: email.trim(),
      password,
      portal,
    }),
  });

  setStoredToken(data.access_token);
  return toAuthUser(data.user);
}

export async function validateSession(): Promise<AuthUser> {
  const user = await request<LoginResponsePayload["user"]>("/auth/me");
  return toAuthUser(user);
}

export function hasSession(): boolean {
  return Boolean(getStoredToken());
}

export async function logout(): Promise<void> {
  setStoredToken(null);
}

export async function requestPasswordReset(email: string): Promise<void> {
  await request<Record<string, never>>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
}

export async function verifyPasswordResetToken(token: string): Promise<{ valid: boolean; role: Role }> {
  return request<{ valid: boolean; role: Role }>("/auth/verify-reset-token", { method: "POST", body: JSON.stringify({ token }) });
}

export async function resetPassword(token: string, newPassword: string): Promise<string> {
  return request<string>("/auth/reset-password", { method: "POST", body: JSON.stringify({ token, new_password: newPassword }) });
}

export function homeRouteForRole(role: Role): string {
  if (role === "ADMIN") return "/admin/dashboard";
  if (role === "MENTOR") return "/mentor/absentees";
  return "/crlr/dashboard";
}
