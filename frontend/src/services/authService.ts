import {
  request,
  getStoredToken,
  getStoredUser,
  setStoredToken,
  setStoredUser,
  ApiError,
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

export async function login(
  email: string,
  password: string,
  portal: "ADMIN" | "CRLR"
): Promise<AuthUser> {
  const data = await request<LoginResponsePayload>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: email.trim(),
      password,
      portal,
    }),
  });

  const authUser: AuthUser = {
    id: data.user.id,
    name: data.user.name,
    email: data.user.email,
    role: data.user.role,
    section: data.user.section,
    year: data.user.year,
  };

  setStoredToken(data.access_token);
  setStoredUser(authUser);

  return authUser;
}

export function persistUser(user: AuthUser | null) {
  setStoredUser(user);
  if (!user) {
    setStoredToken(null);
  }
}

export function readPersistedUser(): AuthUser | null {
  const token = getStoredToken();
  if (!token) {
    setStoredUser(null);
    return null;
  }
  return getStoredUser<AuthUser>();
}

export async function logout(): Promise<void> {
  setStoredToken(null);
  setStoredUser(null);
}

export function homeRouteForRole(role: Role): string {
  return role === "ADMIN" ? "/admin/dashboard" : "/crlr/dashboard";
}
