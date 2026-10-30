/**
 * Centralized Frontend API Client for FastAPI Backend Integration
 */

export const PRODUCTION_API_URL = "https://session-monitoring-system.onrender.com/api";
export const LOCAL_API_URL = "http://localhost:8000/api";

function normalizeApiBaseUrl(url: string): string {
  const withoutTrailingSlashes = url.trim().replace(/\/+$/, "");
  const withoutRepeatedApiPrefixes = withoutTrailingSlashes.replace(/(?:\/api)+$/i, "");
  return `${withoutRepeatedApiPrefixes}/api`;
}

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env["VITE_API_BASE_URL"]?.trim();
  const isLocalUrl = (url: string) =>
    /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?(?:\/|$)/i.test(url);

  // During SSR (server-side rendering at build time), window is undefined.
  if (typeof window === "undefined") {
    if (envUrl && !isLocalUrl(envUrl)) {
      return normalizeApiBaseUrl(envUrl);
    }
    return PRODUCTION_API_URL;
  }

  const hostname = window.location.hostname;
  const browserLocalhost = ["localhost", "127.0.0.1", "[::1]"].includes(hostname);

  if (browserLocalhost) {
    // Running locally in the browser
    if (envUrl && isLocalUrl(envUrl)) {
      return normalizeApiBaseUrl(envUrl);
    }
    return LOCAL_API_URL;
  }

  // Running on deployed frontend (Vercel, custom domain, etc.)
  if (envUrl && !isLocalUrl(envUrl)) {
    return normalizeApiBaseUrl(envUrl);
  }

  // Fallback to production Render backend URL
  return PRODUCTION_API_URL;
}

/** Build a canonical API URL without duplicate /api prefixes. */
export function buildApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const base = normalizeApiBaseUrl(getApiBaseUrl());
  const baseRoot = base.replace(/\/api$/i, "");
  const cleanPath = (path.startsWith("/") ? path : `/${path}`).replace(/^\/api(?=\/|$)/i, "");
  return `${baseRoot}/api${cleanPath}`;
}

const TOKEN_KEY = "fams.auth.token";

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

export async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const isLoginRequest = path === "/auth/login";
  const token = isLoginRequest ? null : getStoredToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // If body is not FormData, default to application/json
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const mergedOptions: RequestInit = {
    mode: "cors",
    ...options,
    headers: {
      ...headers,
      ...(options.headers as Record<string, string>),
    },
  };

  const url = buildApiUrl(path);

  try {
    const response = await fetch(url, mergedOptions);

    if (response.status === 401 && path === "/auth/me" && token) {
      // Validate and clear a stale session during startup. Other request-level
      // 401s stay attached to their operation so a failed upload cannot send
      // the administrator away from the page before its error is shown.
      setStoredToken(null);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("fams:unauthorized"));
      }
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
    const isNetworkError =
      err?.name === "TypeError" ||
      (typeof err?.message === "string" && err.message.toLowerCase().includes("failed to fetch"));
    const friendlyMessage = isNetworkError
      ? "Unable to connect to the backend server. If the server is spinning up after inactivity (Render cold start), please try again in a few seconds."
      : (err?.message || "Failed to connect to the backend server.");
    throw new ApiError(friendlyMessage, 500);
  }
}

export function uploadRequest<T>(
  path: string,
  body: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const url = buildApiUrl(path);
    xhr.open("POST", url);
    const token = getStoredToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress?.(Math.min(100, Math.round((event.loaded / event.total) * 100)));
      }
    };
    xhr.onerror = () =>
      reject(
        new ApiError(
          "Unable to connect to the backend server for upload. Please check your connection and try again.",
          500,
        ),
      );
    xhr.onabort = () => reject(new ApiError("Upload was cancelled.", 0));
    xhr.onload = () => {
      let json: any = null;
      try {
        json = JSON.parse(xhr.responseText);
      } catch {
        json = null;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const message = json?.error?.message || json?.detail || `Request failed with status ${xhr.status}`;
        reject(new ApiError(message, xhr.status, json?.error?.details));
        return;
      }
      if (json && typeof json === "object" && "success" in json && "data" in json) {
        resolve(json.data as T);
      } else {
        resolve(json as T);
      }
    };
    xhr.send(body);
  });
}

/** Triggers an authenticated client-side file download (for Excel templates) */
export async function downloadApiFile(path: string, filename: string) {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = buildApiUrl(path);
  const response = await fetch(url, { headers, mode: "cors" });

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

