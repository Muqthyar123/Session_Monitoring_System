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
  const sid = (sessionId || "").trim();
  if (!sid) {
    throw new Error("Invalid Session ID. Please refresh the page and try again.");
  }
  return request<ClassSession>("/attendance", {
    method: "POST",
    body: JSON.stringify({
      session_id: sid,
      sessionId: sid,
      status: present ? "PRESENT" : "ABSENT",
    }),
  });
}

export async function submitSubstitute(
  sessionId: string,
  substituteName: string
): Promise<ClassSession> {
  const sid = (sessionId || "").trim();
  if (!sid) {
    throw new Error("Invalid Session ID. Please refresh the page and try again.");
  }
  return request<ClassSession>("/attendance", {
    method: "POST",
    body: JSON.stringify({
      session_id: sid,
      sessionId: sid,
      status: "SUBSTITUTE",
      substitute_name: substituteName,
      substituteName: substituteName,
    }),
  });
}

export async function getAlerts(): Promise<AdminAlert[]> {
  return request<AdminAlert[]>("/attendance/alerts");
}

export async function getCRLRAnalytics(_section: string) {
  return request<any>("/crlr/analytics");
}
