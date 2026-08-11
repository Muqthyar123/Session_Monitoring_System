import { mockDelay } from "./apiClient";
import { MOCK_NOTIFICATIONS, type AppNotification } from "@/data/mock/mockData";

let notifications: AppNotification[] = MOCK_NOTIFICATIONS.map((n) => ({ ...n }));

export async function getNotifications(): Promise<AppNotification[]> {
  return mockDelay(notifications.map((n) => ({ ...n })), 400);
}

export async function markNotificationRead(id: string): Promise<void> {
  notifications = notifications.map((n) => (n.id === id ? { ...n, read: true } : n));
  return mockDelay(undefined, 200);
}

export async function markAllNotificationsRead(): Promise<void> {
  notifications = notifications.map((n) => ({ ...n, read: true }));
  return mockDelay(undefined, 250);
}
