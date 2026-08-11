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

export const MOCK_SECTIONS = ["II-A", "II-B", "II-C", "III-A", "III-B"];
export const MOCK_YEARS = ["2nd Year", "3rd Year"];

export const MOCK_DEMO_CREDENTIALS = {
  admin: { email: "admin@example.com", password: "demo1234" },
  cr: { email: "cr@example.com", password: "demo1234" },
  lr: { email: "lr@example.com", password: "demo1234" },
};

export const MOCK_ADMIN_USER: AuthUser = {
  id: "u-admin-1",
  name: "Demo Administrator",
  email: "admin@example.com",
  role: "ADMIN",
};

export const MOCK_CR_USER: AuthUser = {
  id: "u-cr-1",
  name: "Aarav Menon (Demo CR)",
  email: "cr@example.com",
  role: "CR",
  year: "2nd Year",
  section: "II-A",
};

export const MOCK_LR_USER: AuthUser = {
  id: "u-lr-1",
  name: "Divya Rao (Demo LR)",
  email: "lr@example.com",
  role: "LR",
  year: "2nd Year",
  section: "II-A",
};

export const MOCK_CRLR_USERS: CRLRUser[] = [
  { id: "c1", name: "Aarav Menon", rollNumber: "22CS2A01", email: "aarav.menon@example.com", role: "CR", year: "2nd Year", section: "II-A" },
  { id: "c2", name: "Divya Rao", rollNumber: "22CS2A02", email: "divya.rao@example.com", role: "LR", year: "2nd Year", section: "II-A" },
  { id: "c3", name: "Kabir Nair", rollNumber: "22CS2B11", email: "kabir.nair@example.com", role: "CR", year: "2nd Year", section: "II-B" },
  { id: "c4", name: "Meera Iyer", rollNumber: "22CS2B12", email: "meera.iyer@example.com", role: "LR", year: "2nd Year", section: "II-B" },
  { id: "c5", name: "Rohan Das", rollNumber: "22CS2C21", email: "rohan.das@example.com", role: "CR", year: "2nd Year", section: "II-C" },
  { id: "c6", name: "Sanya Kulkarni", rollNumber: "21CS3A05", email: "sanya.k@example.com", role: "CR", year: "3rd Year", section: "III-A" },
  { id: "c7", name: "Vikram Shetty", rollNumber: "21CS3A06", email: "vikram.s@example.com", role: "LR", year: "3rd Year", section: "III-A" },
  { id: "c8", name: "Neha Pillai", rollNumber: "21CS3B14", email: "neha.pillai@example.com", role: "CR", year: "3rd Year", section: "III-B" },
];

export const MOCK_TIMETABLE_UPLOADS: TimetableUpload[] = [
  { id: "t1", academicYear: "2025-2026", section: "II-A", file: "All_Class_Timetables_Format.xlsx", uploadedDate: "2026-07-14", status: "Processed" },
  { id: "t2", academicYear: "2025-2026", section: "II-B", file: "All_Class_Timetables_Format.xlsx", uploadedDate: "2026-07-14", status: "Processed" },
  { id: "t3", academicYear: "2025-2026", section: "III-A", file: "All_Class_Timetables_Format.xlsx", uploadedDate: "2026-07-15", status: "Processing" },
];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const PERIOD_TIMES = [
  { start: "09:10", end: "10:00" },
  { start: "10:00", end: "10:50" },
  { start: "10:50", end: "11:40" },
  { start: "11:40", end: "12:30" },
  { start: "13:20", end: "14:10" },
  { start: "14:10", end: "15:00" },
];
const SUBJECTS = [
  { subject: "Database Management Systems", room: "B-204" },
  { subject: "Operating Systems", room: "B-205" },
  { subject: "Computer Networks", room: "B-206" },
  { subject: "Design & Analysis of Algorithms", room: "B-204" },
  { subject: "DBMS Lab", room: "Lab-3" },
  { subject: "Software Engineering", room: "B-210" },
];

export function buildMockTimetable(year: string, section: string): TimetablePeriod[] {
  const seed = (year.length + section.length) % SUBJECTS.length;
  const rows: TimetablePeriod[] = [];
  DAYS.forEach((day, di) => {
    PERIOD_TIMES.forEach((slot, pi) => {
      const s = SUBJECTS[(di + pi + seed) % SUBJECTS.length]!;
      rows.push({
        day,
        period: pi + 1,
        startTime: slot.start,
        endTime: slot.end,
        subject: s.subject,
        room: s.room,
      });
    });
  });
  return rows;
}

export const MOCK_SESSIONS: ClassSession[] = [
  {
    id: "s1",
    section: "II-A",
    subject: "Database Management Systems",
    period: "Period 1",
    startTime: "09:10",
    endTime: "10:00",
    crlrName: "Aarav Menon",
    crlrRole: "CR",
    sessionStatus: "Active",
    facultyResponse: "Pending",
    responseTime: null,
    substituteName: null,
    responseWindowSecondsRemaining: 522,
    responseWindowExpired: false,
  },
  {
    id: "s2",
    section: "II-A",
    subject: "DBMS Lab (Periods 3-4)",
    period: "Period 3-4",
    startTime: "10:50",
    endTime: "12:30",
    crlrName: "Divya Rao",
    crlrRole: "LR",
    sessionStatus: "Upcoming",
    facultyResponse: "Pending",
    responseTime: null,
    substituteName: null,
    responseWindowSecondsRemaining: null,
    responseWindowExpired: false,
  },
  {
    id: "s3",
    section: "II-B",
    subject: "Operating Systems",
    period: "Period 1",
    startTime: "09:10",
    endTime: "10:00",
    crlrName: "Kabir Nair",
    crlrRole: "CR",
    sessionStatus: "Completed",
    facultyResponse: "Present",
    responseTime: "09:14",
    substituteName: null,
    responseWindowSecondsRemaining: null,
    responseWindowExpired: false,
  },
  {
    id: "s4",
    section: "II-C",
    subject: "Computer Networks",
    period: "Period 2",
    startTime: "10:00",
    endTime: "10:50",
    crlrName: "Rohan Das",
    crlrRole: "CR",
    sessionStatus: "Completed",
    facultyResponse: "Not Present",
    responseTime: "10:06",
    substituteName: null,
    responseWindowSecondsRemaining: null,
    responseWindowExpired: false,
  },
  {
    id: "s5",
    section: "III-A",
    subject: "Software Engineering",
    period: "Period 2",
    startTime: "10:00",
    endTime: "10:50",
    crlrName: "Sanya Kulkarni",
    crlrRole: "CR",
    sessionStatus: "Completed",
    facultyResponse: "Substitute",
    responseTime: "10:05",
    substituteName: "Prof. R. Balaji (substitute)",
    responseWindowSecondsRemaining: null,
    responseWindowExpired: false,
  },
  {
    id: "s6",
    section: "III-B",
    subject: "Design & Analysis of Algorithms",
    period: "Period 1",
    startTime: "09:10",
    endTime: "10:00",
    crlrName: "Neha Pillai",
    crlrRole: "CR",
    sessionStatus: "Completed",
    facultyResponse: "Pending",
    responseTime: null,
    substituteName: null,
    responseWindowSecondsRemaining: 0,
    responseWindowExpired: true,
  },
];

export const MOCK_ALERTS: AdminAlert[] = [
  { id: "a1", section: "II-C", subject: "Computer Networks", session: "10:00 - 10:50", time: "10:06", reportedBy: "CR", reason: "Faculty not available", status: "New" },
  { id: "a2", section: "III-B", subject: "Design & Analysis of Algorithms", session: "09:10 - 10:00", time: "09:20", reportedBy: "CR", reason: "No response within 10 minutes", status: "New" },
  { id: "a3", section: "II-B", subject: "Operating Systems", session: "14:10 - 15:00", time: "14:21", reportedBy: "LR", reason: "No response within 10 minutes", status: "Acknowledged" },
];

export const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: "n1",
    title: "Faculty Attendance Required",
    section: "II-A",
    subject: "DBMS",
    time: "09:10 - 10:00",
    message: "Please confirm whether the faculty is present.",
    read: false,
    sessionId: "s1",
  },
  {
    id: "n2",
    title: "Upcoming Session",
    section: "II-A",
    subject: "DBMS Lab",
    time: "10:50 - 12:30",
    message: "A combined session starts soon. One response is required for the full block.",
    read: false,
    sessionId: "s2",
  },
  {
    id: "n3",
    title: "Response Recorded",
    section: "II-A",
    subject: "Operating Systems",
    time: "Yesterday, 14:10 - 15:00",
    message: "Your response (Faculty Present) was recorded.",
    read: true,
    sessionId: null,
  },
];

export const MOCK_ADMIN_DASHBOARD = {
  date: "2026-08-11",
  summary: {
    totalSections: 5,
    totalCRs: 5,
    totalLRs: 3,
    todaysSessions: 24,
    facultyPresent: 17,
    facultyAbsent: 3,
    pendingResponses: 2,
    substituteFaculty: 2,
  },
  facultyPresencePercent: 78,
  sectionWise: [
    { section: "II-A", present: 5, absent: 1, substitute: 0 },
    { section: "II-B", present: 4, absent: 0, substitute: 1 },
    { section: "II-C", present: 3, absent: 1, substitute: 0 },
    { section: "III-A", present: 3, absent: 0, substitute: 1 },
    { section: "III-B", present: 2, absent: 1, substitute: 0 },
  ],
  sessionStatus: [
    { name: "Responded", value: 17 },
    { name: "Pending", value: 2 },
    { name: "Faculty Absent", value: 3 },
    { name: "Substitute Reported", value: 2 },
  ],
};

export const MOCK_CRLR_ANALYTICS = {
  section: "II-A",
  summary: { facultyPresent: 22, facultyAbsent: 3, substitute: 2, responseRate: 92 },
  daily: [
    { day: "Mon", present: 5, absent: 1, substitute: 0 },
    { day: "Tue", present: 6, absent: 0, substitute: 0 },
    { day: "Wed", present: 4, absent: 1, substitute: 1 },
    { day: "Thu", present: 3, absent: 1, substitute: 1 },
    { day: "Fri", present: 4, absent: 0, substitute: 0 },
  ],
  weekly: [
    { week: "W1", presencePercent: 88 },
    { week: "W2", presencePercent: 92 },
    { week: "W3", presencePercent: 81 },
    { week: "W4", presencePercent: 95 },
  ],
  responseStatus: [
    { name: "Responded", value: 24 },
    { name: "Pending", value: 1 },
    { name: "Expired", value: 2 },
  ],
};
