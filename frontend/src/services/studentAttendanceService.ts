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
  reason?: string;
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

export async function getCRLRStudents(): Promise<StudentItem[]> {
  return request<StudentItem[]>("/crlr/students");
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
