import { request } from "./apiClient";
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
