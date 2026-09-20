/**
 * MOCK DATA — DEMO ONLY.
 * All names, sections and records below are fictional and exist only to
 * demonstrate the UI. Delete this file once real APIs are connected.
 */

export type Role = "ADMIN" | "CR" | "LR";
export type SessionStatus = "Upcoming" | "Active" | "Completed";
export type FacultyResponse = "Pending" | "Present" | "Not Present" | "Substitute";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  year?: string;
  section?: string;
}

export interface CRLRUser {
  id: string;
  name: string;
  rollNumber: string;
  email: string;
  role: "CR" | "LR";
  year: string;
  section: string;
}

export interface TimetableUpload {
  id: string;
  academicYear: string;
  section: string;
  file: string;
  uploadedDate: string;
  status: "Processed" | "Processing" | "Failed";
}

export interface TimetablePeriod {
  day: string;
  period: number;
  startTime: string;
  endTime: string;
  subject: string;
  room: string;
}

export interface ClassSession {
  id: string;
  section: string;
  subject: string;
  faculty?: string;
  period: string;
  startTime: string;
  endTime: string;
  crlrName: string;
  crlrRole: "CR" | "LR";
  sessionStatus: SessionStatus;
  facultyResponse: FacultyResponse;
  responseTime: string | null;
  substituteName: string | null;
  /** Provided by the backend. Frontend only displays it. */
  responseWindowSecondsRemaining: number | null;
  responseWindowExpired: boolean;
}

export interface AdminAlert {
  id: string;
  section: string;
  subject: string;
  session: string;
  time: string;
  reportedBy: "CR" | "LR";
  reason: "Faculty not available" | "No response within 10 minutes";
  status: "New" | "Acknowledged";
}

export interface AppNotification {
  id: string;
  title: string;
  section: string;
  subject: string;
  time: string;
  message: string;
  read: boolean;
  sessionId: string | null;
}

export const MOCK_SECTIONS: string[] = [];
export const MOCK_YEARS: string[] = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

export const MOCK_DEMO_CREDENTIALS = {
  admin: { email: "admin@example.com", password: "demo1234" },
  cr: { email: "cr@example.com", password: "demo1234" },
  lr: { email: "lr@example.com", password: "demo1234" },
};

export const MOCK_ADMIN_USER: AuthUser = {
  id: "u-admin-1",
  name: "System Administrator",
  email: "admin@example.com",
  role: "ADMIN",
};

export const MOCK_CR_USER: AuthUser | null = null;
export const MOCK_LR_USER: AuthUser | null = null;

export const MOCK_CRLR_USERS: CRLRUser[] = [];
export const MOCK_TIMETABLE_UPLOADS: TimetableUpload[] = [];

export function buildMockTimetable(_year: string, _section: string): TimetablePeriod[] {
  return [];
}

export const MOCK_SESSIONS: ClassSession[] = [];
export const MOCK_ALERTS: AdminAlert[] = [];
export const MOCK_NOTIFICATIONS: AppNotification[] = [];

export const MOCK_ADMIN_DASHBOARD = {
  date: new Date().toISOString().split("T")[0],
  summary: {
    totalSections: 0,
    totalCRs: 0,
    totalLRs: 0,
    todaysSessions: 0,
    facultyPresent: 0,
    facultyAbsent: 0,
    pendingResponses: 0,
    substituteFaculty: 0,
  },
  facultyPresencePercent: 0,
  sectionWise: [],
  sessionStatus: [],
};

export const MOCK_CRLR_ANALYTICS = {
  section: "",
  summary: { facultyPresent: 0, facultyAbsent: 0, substitute: 0, responseRate: 0 },
  daily: [],
  weekly: [],
  responseStatus: [],
};
