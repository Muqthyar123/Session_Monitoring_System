import { mockDelay } from "./apiClient";
import {
  MOCK_ADMIN_DASHBOARD,
  MOCK_CRLR_ANALYTICS,
  MOCK_SESSIONS,
  MOCK_ALERTS,
  type AdminAlert,
  type ClassSession,
} from "@/data/mock/mockData";

let sessions: ClassSession[] = MOCK_SESSIONS.map((s) => ({ ...s }));

export async function getAdminDashboard() {
  return mockDelay(MOCK_ADMIN_DASHBOARD, 500);
}

export async function getSessions(section?: string): Promise<ClassSession[]> {
  const data = section ? sessions.filter((s) => s.section === section) : sessions;
  return mockDelay(data.map((s) => ({ ...s })), 450);
}

/** Sessions the backend has marked as Active/Upcoming for a section. */
export async function getActiveSessions(section: string): Promise<ClassSession[]> {
  const data = sessions.filter((s) => s.section === section && s.sessionStatus !== "Completed");
  return mockDelay(data.map((s) => ({ ...s })), 450);
}

export async function getSession(id: string): Promise<ClassSession | null> {
  const found = sessions.find((s) => s.id === id) ?? null;
  return mockDelay(found ? { ...found } : null, 300);
}

export async function submitFacultyAttendance(
  sessionId: string,
  present: boolean,
): Promise<ClassSession> {
  return applyResponse(sessionId, {
    facultyResponse: present ? "Present" : "Not Present",
    substituteName: null,
  });
}

export async function submitSubstitute(
  sessionId: string,
  substituteName: string,
): Promise<ClassSession> {
  return applyResponse(sessionId, {
    facultyResponse: "Substitute",
    substituteName,
  });
}

function applyResponse(sessionId: string, patch: Partial<ClassSession>): Promise<ClassSession> {
  const now = new Date();
  const responseTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  let updated: ClassSession | null = null;
  sessions = sessions.map((s) => {
    if (s.id !== sessionId) return s;
    updated = { ...s, ...patch, responseTime, responseWindowSecondsRemaining: null };
    return updated;
  });
  if (!updated) return Promise.reject(new Error("Session not found."));
  return mockDelay(updated as ClassSession, 600);
}

export async function getAlerts(): Promise<AdminAlert[]> {
  return mockDelay(MOCK_ALERTS, 450);
}

export async function getCRLRAnalytics(_section: string) {
  return mockDelay(MOCK_CRLR_ANALYTICS, 500);
}
