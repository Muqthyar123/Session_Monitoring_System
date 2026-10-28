import { request } from "./apiClient";

export interface UploadHistoryRecord {
  id: string;
  actor_id?: string;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export function getUploadHistory(skip = 0, limit = 10): Promise<UploadHistoryRecord[]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  return request<UploadHistoryRecord[]>(`/admin/uploads/history?${params.toString()}`);
}
