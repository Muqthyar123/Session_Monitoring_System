/**
 * Frontend API abstraction.
 *
 * Every service in this folder returns mock data today. When the FastAPI
 * backend exists, replace the body of each service function with a real
 * `request()` call — component code does not need to change.
 */

export const API_BASE_URL = "/api";

export const MOCK_MODE = true;

/** Simulates network latency for mock services. */
export function mockDelay<T>(data: T, ms = 450): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 500) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Placeholder for the real HTTP layer (not used while MOCK_MODE is true). */
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!response.ok) throw new ApiError(`Request failed: ${path}`, response.status);
  return (await response.json()) as T;
}

/** Triggers a client-side file download for template files. */
export function downloadFile(filename: string, contents: string, mime = "text/csv") {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
