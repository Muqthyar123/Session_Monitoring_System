import { request } from "./apiClient";
import type { AdminAlert, ClassSession } from "@/data/mock/mockData";

export interface AdminDashboardData {
  date: string;
  summary: {
    totalSections: number;
    totalCRs: number;
    totalLRs: number;
    todaysSessions: number;
    facultyPresent: number;
    facultyAbsent: number;
    substituteFaculty: number;
    pendingResponses: number;
  };
  facultyPresencePercent: number;
  sectionWise: Array<{ section: string; present: number; absent: number; substitute: number }>;
  yearCards: Array<{
    year: string;
    totalSections: number;
    totalClasses: number;
    facultyCount: number;
    present: number;
    absent: number;
    substitute: number;
    late: number;
    presencePercent: number;
    sections: Array<{
      section: string;
      year: string;
      totalClasses: number;
      facultyCount: number;
      present: number;
      absent: number;
      substitute: number;
      late: number;
      presencePercent: number;
    }>;
  }>;
  sectionsCards: Array<{
    section: string;
    year: string;
    totalClasses: number;
    facultyCount: number;
    present: number;
    absent: number;
    substitute: number;
    late: number;
    presencePercent: number;
  }>;
  facultyAnalytics: Array<{
    facultyName: string;
    subject: string;
    section: string;
    year?: string;
    totalClasses: number;
    attendedClasses: number;
    absentClasses: number;
    lateClasses?: number;
    substitutedClasses: number;
    totalHours: number;
    attendedHours: number;
    absentHours: number;
    lateHours?: number;
    substitutedHours: number;
    attendancePercentage: number;
  }>;
  sessionStatus: Array<{ name: string; value: number }>;
}

export async function getAdminDashboard(): Promise<AdminDashboardData> {
  return request<AdminDashboardData>("/admin/analytics");
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

export async function getAlerts(category?: string, status?: string, dates?: { fromDate?: string; toDate?: string }): Promise<AdminAlert[]> {
  const params = new URLSearchParams();
  if (category && category !== "ALL") params.append("category", category);
  if (status && status !== "ALL") params.append("status", status);
  if (dates?.fromDate) params.append("fromDate", dates.fromDate);
  if (dates?.toDate) params.append("toDate", dates.toDate);
  const qs = params.toString();
  const result = await request<AdminAlert[] | { items?: AdminAlert[]; total?: number }>(`/attendance/alerts${qs ? `?${qs}` : ""}`);
  const rows = Array.isArray(result) ? result : result?.items ?? [];
  return filterAlertDates(rows, dates);
}

export interface AdminAlertHistory { items: AdminAlert[]; total: number; page: number; limit: number }
function filterAlertDates(rows: AdminAlert[], dates?: { fromDate?: string; toDate?: string }) {
  if (!dates?.fromDate && !dates?.toDate) return rows;
  const dayInKolkata = (value?: string) => value ? new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value)) : "";
  return rows.filter((row) => {
    const day = dayInKolkata(row.created_at);
    return !!day && (!dates.fromDate || day >= dates.fromDate) && (!dates.toDate || day <= dates.toDate);
  });
}

export async function getAdminAlertHistory(filters: { category?: string; status?: string; fromDate?: string; toDate?: string; page?: number; limit?: number; search?: string }): Promise<AdminAlertHistory> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, String(value));
  const result = await request<AdminAlertHistory | AdminAlert[]>(`/attendance/alerts?${params.toString()}`);
  if (!Array.isArray(result)) return { items: result?.items ?? [], total: result?.total ?? 0, page: result?.page ?? filters.page ?? 1, limit: result?.limit ?? filters.limit ?? 50 };

  // Backward compatibility while the frontend and backend deployments roll out independently.
  let rows = filterAlertDates(result, filters);
  if (filters.status && filters.status !== "ALL") rows = rows.filter((row) => (row.status || "New").toLowerCase() === filters.status!.toLowerCase());
  if (filters.category && filters.category !== "ALL") rows = rows.filter((row) => {
    const reason = (row.reason || "").toLowerCase();
    return filters.category === "NO_RESPONSE_10MIN" ? reason.includes("10 min") || reason.includes("no response") : filters.category === "FACULTY_ABSENT" ? reason.includes("not available") || reason.includes("absent") || reason.includes("substitute") : reason.includes("update") || reason.includes("status");
  });
  if (filters.search) {
    const needle = filters.search.toLowerCase();
    rows = rows.filter((row) => [row.reason, row.section, row.subject, row.session, row.reportedBy].some((value) => String(value || "").toLowerCase().includes(needle)));
  }
  const limit = filters.limit ?? 50;
  const page = filters.page ?? 1;
  return { items: rows.slice((page - 1) * limit, page * limit), total: rows.length, page, limit };
}

export async function acknowledgeAlert(alertId: string): Promise<any> {
  return request<any>(`/attendance/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
  });
}

export async function getCRLRAnalytics(_section: string) {
  return request<any>("/crlr/analytics");
}

