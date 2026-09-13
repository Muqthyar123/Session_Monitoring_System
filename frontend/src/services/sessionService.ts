import { request } from "./apiClient";
import type { AdminAlert, ClassSession } from "@/data/mock/mockData";

export async function getAdminDashboard() {
  return request<any>("/admin/analytics");
}

export async function getSessions(section?: string): Promise<ClassSession[]> {
  const query = section ? `?section=${encodeURIComponent(section)}` : "";
  return request<ClassSession[]>(`/sessions/today${query}`);
}

export async function getActiveSessions(section: string): Promise<ClassSession[]> {
  const query = section ? `?section=${encodeURIComponent(section)}` : "";
  return request<ClassSession[]>(`/sessions/active${query}`);
}

export async function getSession(id: string): Promise<ClassSession | null> {
  return request<ClassSession>(`/sessions/${id}`);
}

export async function submitFacultyAttendance(
  sessionId: string,
  present: boolean
): Promise<ClassSession> {
  return request<ClassSession>("/attendance", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      status: present ? "PRESENT" : "ABSENT",
    }),
  });
}

export async function submitSubstitute(
  sessionId: string,
  substituteName: string
): Promise<ClassSession> {
  return request<ClassSession>("/attendance", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      status: "SUBSTITUTE",
      substitute_name: substituteName,
    }),
  });
}

export async function getAlerts(): Promise<AdminAlert[]> {
  return request<AdminAlert[]>("/attendance/alerts");
}

export async function getCRLRAnalytics(_section: string) {
  return request<any>("/crlr/analytics");
}
