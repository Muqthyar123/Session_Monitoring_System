/**
 * Centralized Frontend API Client for FastAPI Backend Integration
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const TOKEN_KEY = "fams.auth.token";
const USER_KEY = "fams.auth.user";

export class ApiError extends Error {
  status: number;
  details?: any;

  constructor(message: string, status = 500, details?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getStoredUser<T>(): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function setStoredUser<T>(user: T | null) {
  if (typeof window === "undefined") return;
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // If body is not FormData, default to application/json
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const mergedOptions: RequestInit = {
    ...options,
    headers: {
      ...headers,
      ...(options.headers as Record<string, string>),
    },
  };

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  try {
    const response = await fetch(url, mergedOptions);

    if (response.status === 401) {
      // Clear token and user on 401 Unauthorized
      setStoredToken(null);
      setStoredUser(null);
    }

    const json = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg =
        json?.error?.message ||
        json?.detail ||
        `Request failed with status ${response.status}`;
      throw new ApiError(errorMsg, response.status, json?.error?.details);
    }

    // Unwrap standard FastAPI response payload { success: true, data: T } if present
    if (json && typeof json === "object" && "success" in json && "data" in json) {
      return json.data as T;
    }

    return json as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      err.message || "Failed to connect to the backend server.",
      500
    );
  }
}

/** Triggers an authenticated client-side file download (for Excel templates) */
export async function downloadApiFile(path: string, filename: string) {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const response = await fetch(url, { headers });

  if (!response.ok) {
    throw new ApiError(`Failed to download template file`, response.status);
  }

  const blob = await response.blob();
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(blobUrl);
}

/** Fallback helper for simulated delay if needed */
export function mockDelay<T>(data: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}
