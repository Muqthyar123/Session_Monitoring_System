import { request } from "./apiClient";
import type { AppNotification } from "@/data/mock/mockData";

export async function getNotifications(): Promise<AppNotification[]> {
  return request<AppNotification[]>("/notifications");
}

export async function markNotificationRead(id: string): Promise<void> {
  return request<void>(`/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead(): Promise<void> {
  return request<void>("/notifications/read-all", {
    method: "PATCH",
  });
}
