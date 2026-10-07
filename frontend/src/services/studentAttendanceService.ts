import { request } from "./apiClient";
import type { StudentItem } from "./studentService";

export interface AbsenteeStudentItem {
  id: string;
  date: string;
  year: string;
  section: string;
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
  submittedBy?: string | null;
  submittedByRole?: string | null;
  submittedAt?: string | null;
  absentCount: number;
  absentRolls: string[];
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
  absentees: Array<{
    rollNumber: string;
    studentId?: string;
    studentName: string;
    studentPhone?: string;
    parentPhone?: string;
  }>;
}): Promise<{ message: string; absent_count: number }> {
  return request<any>("/crlr/student-attendance", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAbsenteeYears(): Promise<string[]> {
  return request<string[]>("/mentor/absentees/years");
}

export async function getAbsenteeSections(year: string): Promise<string[]> {
  return request<string[]>(`/mentor/absentees/sections?year=${encodeURIComponent(year)}`);
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
