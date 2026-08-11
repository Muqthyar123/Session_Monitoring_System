import { mockDelay, ApiError } from "./apiClient";
import {
  MOCK_ADMIN_USER,
  MOCK_CR_USER,
  MOCK_LR_USER,
  MOCK_DEMO_CREDENTIALS,
  type AuthUser,
  type Role,
} from "@/data/mock/mockData";

const STORAGE_KEY = "fams.demo.user";

/** MOCK login. Real authentication (JWT) will be handled by the backend. */
export async function login(
  email: string,
  password: string,
  portal: "ADMIN" | "CRLR",
): Promise<AuthUser> {
  const normalized = email.trim().toLowerCase();
  const c = MOCK_DEMO_CREDENTIALS;

  let user: AuthUser | null = null;
  if (normalized === c.admin.email && password === c.admin.password) user = MOCK_ADMIN_USER;
  if (normalized === c.cr.email && password === c.cr.password) user = MOCK_CR_USER;
  if (normalized === c.lr.email && password === c.lr.password) user = MOCK_LR_USER;

  if (!user) throw new ApiError("Invalid email or password.", 401);

  if (portal === "ADMIN" && user.role !== "ADMIN") {
    throw new ApiError("This account is not an administrator account.", 403);
  }
  if (portal === "CRLR" && user.role === "ADMIN") {
    throw new ApiError("Administrators must use the Admin login page.", 403);
  }

  return mockDelay(user, 600);
}

export function persistUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  else window.localStorage.removeItem(STORAGE_KEY);
}

export function readPersistedUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  persistUser(null);
  return mockDelay(undefined, 150);
}

export function homeRouteForRole(role: Role): string {
  return role === "ADMIN" ? "/admin/dashboard" : "/crlr/dashboard";
}
