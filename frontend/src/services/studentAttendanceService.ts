import { request } from "./apiClient";
import { downloadApiFile } from "./apiClient";
import type { StudentItem } from "./studentService";

export interface AbsenteeStudentItem {
  id: string;
  _id?: string;
  date: string;
  year: string;
  section: string;
  sessionId?: string;
  rollNumber: string;
  studentId?: string;
  studentName: string;
  studentPhone?: string;
  parentPhone?: string;
  submittedBy?: string;
  status: string;
  originalStatus?: string;
  subject?: string;
  faculty?: string;
  session?: string;
  reason?: string;
  reasonUpdatedBy?: string;
  correctionReason?: string;
  correctedBy?: string;
  correctedByRole?: string;
  correctedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface StudentAnalyticsSummaryItem {
  studentId?: string;
  studentName: string;
  rollNumber: string;
  year: string;
  section: string;
  studentPhone?: string;
  parentPhone?: string;
  totalAbsences: number;
  totalDays: number;
  attendancePercentage: number;
}

export interface StudentAttendanceSubmissionStatus {
  isSubmittedToday: boolean;
  date: string;
  year: string;
  section: string;
  sessions: Array<{sessionId: "SESSION_1" | "SESSION_2"; label: string; startTime: string; endTime: string; isOpen: boolean; isSubmitted: boolean; submittedBy?: string | null; submittedByRole?: string | null; submittedAt?: string | null; absentCount: number; absentRolls: string[]; status: string}>;
  timetable: {configured: boolean; reason?: string; workingDay?: boolean};
}

export interface AttendanceDraft {
  id: string;
  absent_rolls: string[];
  status: "DRAFT" | "SUBMITTED" | "EXPIRED";
  version: number;
}
export interface AttendanceControlStatus {
  date: string;
  sessionId: string;
  suspended: boolean;
  suspensions: Array<{ startDate: string; endDate: string; reason?: string | null }>;
  draft: AttendanceDraft | null;
}

export function getAttendanceControlStatus(year: string, section: string, date: string, sessionId: string, attendanceType: "STUDENT" | "FACULTY" = "STUDENT") {
  const params = new URLSearchParams({ year, section, date, sessionId, attendanceType });
  return request<AttendanceControlStatus>(`/crlr/attendance-control?${params}`);
}

export function saveAttendanceDraft(payload: { year: string; section: string; date: string; sessionId: string; absentRolls: string[]; version?: number }) {
  return request<AttendanceDraft>("/crlr/attendance-draft", { method: "PUT", body: JSON.stringify(payload) });
}

export interface AttendanceSuspension { id: string; years: string[]; sections_by_year: Record<string, string[]>; all_sections_years: string[]; start_date: string; end_date: string; attendance_type: "STUDENT" | "FACULTY" | "BOTH"; reason?: string; status: string; created_by?: string; }
export const getAttendanceSuspensions = () => request<AttendanceSuspension[]>("/admin/attendance-suspensions");
export async function createAttendanceSuspension(
  payload: { years: string[]; sectionsByYear: Record<string, string[]>; allSectionsYears: string[]; startDate: string; endDate: string; attendanceType: string; reason?: string },
  onRetry?: (attempt: number) => void,
) {
  const idBytes = crypto.getRandomValues(new Uint8Array(12));
  const requestId = Array.from(idBytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  const body = JSON.stringify({ ...payload, requestId });
  const retryDelays = [1500, 3000, 6000, 10000];
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await request<AttendanceSuspension>("/admin/attendance-suspensions", { method: "POST", body });
    } catch (error: any) {
      const transient = [0, 408, 502, 503, 504].includes(error?.status);
      if (!transient || attempt >= retryDelays.length) throw error;
      onRetry?.(attempt + 1);
      await new Promise((resolve) => window.setTimeout(resolve, retryDelays[attempt]));
    }
  }
}
export const cancelAttendanceSuspension = (id: string) => request<{ id: string }>(`/admin/attendance-suspensions/${encodeURIComponent(id)}/cancel`, { method: "POST" });

export async function downloadAbsenteeHistory(filters: { format: "pdf" | "xlsx" | "csv"; year?: string | null | undefined; branch?: string | undefined; section?: string | null | undefined; rollNumber?: string | undefined; fromDate?: string | undefined; toDate?: string | undefined }) {
  const params = new URLSearchParams({ format: filters.format });
  if (filters.year) params.set("year", filters.year);
  if (filters.branch) params.set("branch", filters.branch);
  if (filters.section) params.set("section", filters.section);
  if (filters.rollNumber) params.set("rollNumber", filters.rollNumber);
  if (filters.fromDate) params.set("fromDate", filters.fromDate);
  if (filters.toDate) params.set("toDate", filters.toDate);
  const extension = filters.format;
  return downloadApiFile(`/history/absentee-export?${params.toString()}`, `Absentee_History.${extension}`);
}

export function initiateAbsenteeCall(payload: { attendanceId: string; phoneNumber: string; contactType: "PARENT" | "STUDENT"; clientCallId: string }) {
  return request<{ id: string }>("/history/calls/initiate", { method: "POST", body: JSON.stringify(payload) });
}
export function updateAbsenteeCallOutcome(callId: string, payload: { outcome: string; followUpNotes?: string }) {
  return request<{ id: string }>(`/history/calls/${encodeURIComponent(callId)}/outcome`, { method: "PATCH", body: JSON.stringify(payload) });
}
export interface AbsenteeCallRecord { id: string; contact_type: "PARENT" | "STUDENT"; phone_number: string; staff_name: string; initiated_at: string; outcome?: string | null; follow_up_notes?: string; outcome_updated_at?: string; outcome_updated_by?: string; }
export const getAbsenteeCallHistory = (attendanceId: string) => request<AbsenteeCallRecord[]>(`/history/calls?attendanceId=${encodeURIComponent(attendanceId)}`);

export interface AbsenteeYearSummary {
  year: string;
  studentCount?: number;
  absenteeCount?: number;
  unassignedStudentCount?: number;
}

export interface AbsenteeSectionSummary {
  section: string;
  year?: string;
  studentCount?: number;
  absenteeCount?: number;
}

export interface AdminStudentAttendanceSummary {
  date: string;
  sessions: Array<{year: string; branch?: string; section: string; sessionId: string; present: number; absent: number; total: number; attendancePercentage: number; submittedBy?: string; submittedAt?: string; status: string}>;
  totalPresent: number;
  totalAbsent: number;
  completedSubmissions: number;
}

export async function getAdminStudentAttendanceSummary(date?: string): Promise<AdminStudentAttendanceSummary> {
  const query = date ? `?date=${encodeURIComponent(date)}` : "";
  return request<AdminStudentAttendanceSummary>(`/admin/student-attendance/summary${query}`);
}

export async function getCRLRStudents(): Promise<StudentItem[]> {
  return request<StudentItem[]>("/crlr/students");
}

export async function getCRLRSubmissionStatus(year?: string, section?: string): Promise<StudentAttendanceSubmissionStatus> {
  const params = new URLSearchParams();
  if (year) params.append("year", year);
  if (section) params.append("section", section);
  const qStr = params.toString() ? `?${params.toString()}` : "";
  return request<StudentAttendanceSubmissionStatus>(`/crlr/student-attendance/status${qStr}`);
}

export async function submitStudentAttendance(payload: {
  year: string;
  section: string;
  sessionId: "SESSION_1" | "SESSION_2";
  absentees: Array<{
    rollNumber: string;
    studentId?: string;
    studentName: string;
    studentPhone?: string;
    parentPhone?: string;
  }>;
}): Promise<{ message: string; absent_count: number; session_id: string }> {
  return request<any>("/crlr/student-attendance", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAbsenteeYears(): Promise<Array<AbsenteeYearSummary | string>> {
  return request<Array<AbsenteeYearSummary | string>>("/mentor/absentees/years");
}

export async function getAbsenteeSections(year: string): Promise<Array<AbsenteeSectionSummary | string>> {
  return request<Array<AbsenteeSectionSummary | string>>(`/mentor/absentees/sections?year=${encodeURIComponent(year)}`);
}

export async function getAbsenteeStudents(year: string, section: string, date?: string): Promise<AbsenteeStudentItem[]> {
  const queryDate = date ? `&date=${encodeURIComponent(date)}` : "";
  return request<AbsenteeStudentItem[]>(
    `/mentor/absentees?year=${encodeURIComponent(year)}&section=${encodeURIComponent(section)}${queryDate}`
  );
}

export async function saveAbsenceReason(recordId: string, reason: string): Promise<AbsenteeStudentItem> {
  return request<AbsenteeStudentItem>(`/mentor/absentees/${recordId}/reason`, {
    method: "PUT",
    body: JSON.stringify({ reason }),
  });
}

export async function getStudentAnalyticsSummary(year: string, section: string): Promise<StudentAnalyticsSummaryItem[]> {
  return request<StudentAnalyticsSummaryItem[]>(
    `/analytics/student-summary?year=${encodeURIComponent(year)}&section=${encodeURIComponent(section)}`
  );
}

export async function getStudentCompleteHistory(rollNumber: string): Promise<AbsenteeStudentItem[]> {
  return request<AbsenteeStudentItem[]>(
    `/analytics/student-history?rollNumber=${encodeURIComponent(rollNumber)}`
  );
}

export async function correctStudentAttendance(payload: {
  recordId?: string;
  rollNumber?: string;
  date?: string;
  sessionId?: "SESSION_1" | "SESSION_2";
  newStatus?: string;
  reason: string;
}): Promise<AbsenteeStudentItem> {
  const url = payload.recordId
    ? `/crlr/student-attendance/${encodeURIComponent(payload.recordId)}/correct`
    : `/crlr/student-attendance/correct`;
  return request<AbsenteeStudentItem>(url, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
