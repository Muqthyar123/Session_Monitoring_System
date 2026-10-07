import { request } from "./apiClient";
import type { AdminAlert, ClassSession } from "@/data/mock/mockData";

export async function getAdminDashboard() {
  return request<any>("/admin/analytics");
}

export interface SessionFilterParams {
  section?: string;
  year?: string;
  branch?: string;
  status?: string;
  date?: string;
}

export async function getSessions(params?: SessionFilterParams | string): Promise<ClassSession[]> {
  const queryParams = new URLSearchParams();
  if (typeof params === "string") {
    if (params && params !== "ALL") queryParams.append("section", params);
  } else if (params) {
    if (params.section && params.section !== "ALL") queryParams.append("section", params.section);
    if (params.year && params.year !== "ALL") queryParams.append("year", params.year);
    if (params.branch && params.branch !== "ALL") queryParams.append("branch", params.branch);
    if (params.status && params.status !== "ALL") queryParams.append("status", params.status);
    if (params.date) queryParams.append("date", params.date);
  }
  const qs = queryParams.toString();
  return request<ClassSession[]>(`/sessions/today${qs ? `?${qs}` : ""}`);
}

export async function getActiveSessions(section: string): Promise<ClassSession[]> {
  const query = section ? `?section=${encodeURIComponent(section)}` : "";
  return request<ClassSession[]>(`/sessions/active${query}`);
}

export async function getSession(id: string): Promise<ClassSession | null> {
  return request<ClassSession>(`/sessions/${id}`);
}

export async function getFacultyHistory(
  facultyName: string,
  period = "this_month",
  startDate?: string,
  endDate?: string,
  section?: string,
  year?: string,
): Promise<any> {
  const params = new URLSearchParams();
  if (period) params.append("period", period);
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  if (section && section !== "ALL") params.append("section", section);
  if (year && year !== "ALL") params.append("year", year);

  const qs = params.toString();
  return request<any>(`/analytics/faculty/${encodeURIComponent(facultyName)}/history${qs ? `?${qs}` : ""}`);
}

export async function submitFacultyAttendance(
  sessionId: string,
  present: boolean,
  arrivalTime?: string,
  arrivalComment?: string
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
      arrival_time: arrivalTime,
      arrivalTime: arrivalTime,
      arrival_comment: arrivalComment,
      arrivalComment: arrivalComment,
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

export async function getAlerts(category?: string, status?: string): Promise<AdminAlert[]> {
  const params = new URLSearchParams();
  if (category && category !== "ALL") params.append("category", category);
  if (status && status !== "ALL") params.append("status", status);
  const qs = params.toString();
  return request<AdminAlert[]>(`/attendance/alerts${qs ? `?${qs}` : ""}`);
}

export async function acknowledgeAlert(alertId: string): Promise<any> {
  return request<any>(`/attendance/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
  });
}

export async function getCRLRAnalytics(_section: string) {
  return request<any>("/crlr/analytics");
}

