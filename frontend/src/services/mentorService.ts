import { request, uploadRequest, downloadApiFile } from "./apiClient";
import type { StudentItem } from "./studentService";
import type { AbsenteeStudentItem } from "./studentAttendanceService";

export interface MentorItem {
  id: string;
  name: string;
  mentorId: string;
  email: string;
  phone?: string;
  designation?: string;
  department?: string;
  profile?: string;
  role: "MENTOR";
  createdAt?: string;
}

export interface MentorCreatePayload {
  name: string;
  mentorId: string;
  email?: string;
  password?: string;
  phone?: string;
  designation?: string;
  department?: string;
  profile?: string;
}

export interface MentorUpdatePayload {
  name?: string;
  mentorId?: string;
  email?: string;
  password?: string;
  phone?: string;
  designation?: string;
  department?: string;
  profile?: string;
}

export interface MentorYearCardItem {
  year: string;
  studentCount: number;
  absenteeCount: number;
}

export interface MentorSectionCardItem {
  section: string;
  year: string;
  studentCount: number;
  absenteeCount: number;
}

export interface MentorDashboardData {
  mentorInfo: {
    id: string;
    name: string;
    email?: string;
    mentorId?: string;
    phone?: string;
    department?: string;
    designation?: string;
    role: string;
  };
  totalStudents: number;
  totalAbsenteesToday: number;
  yearCounts: MentorYearCardItem[];
  sectionCounts: MentorSectionCardItem[];
}

// ----------------------------------------------------
// ADMIN MENTOR MANAGEMENT ENDPOINTS
// ----------------------------------------------------

export async function getMentors(search?: string): Promise<MentorItem[]> {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<MentorItem[]>(`/admin/mentors${query}`);
}

export async function createMentor(data: MentorCreatePayload): Promise<MentorItem> {
  return request<MentorItem>("/admin/mentors", {
    method: "POST",
    body: JSON.stringify({
      ...data,
      rollNumber: data.mentorId,
      role: "MENTOR",
    }),
  });
}

export async function updateMentor(id: string, data: MentorUpdatePayload): Promise<MentorItem> {
  return request<MentorItem>(`/admin/mentors/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      ...data,
      rollNumber: data.mentorId,
    }),
  });
}

export async function deleteMentor(id: string): Promise<void> {
  return request<void>(`/admin/mentors/${id}`, {
    method: "DELETE",
  });
}

export async function resetMentors(): Promise<{ message: string; deleted_count?: number }> {
  return request<{ message: string; deleted_count?: number }>("/admin/mentors/reset", {
    method: "DELETE",
  });
}

export async function uploadMentorExcel(file: File, onProgress?: (percent: number) => void): Promise<{ message: string; created?: number; updated?: number; failed?: number; status: "success" | "warning" | "error"; details: string[] }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await uploadRequest<any>("/admin/mentors/import", formData, onProgress);

  const created = Number(res.created ?? 0);
  const updated = Number(res.updated ?? 0);
  const failed = Number(res.failed ?? 0);
  const changed = created + updated;
  const status = failed === 0 ? "success" : changed > 0 ? "warning" : "error";
  const verb = status === "error" ? "Import failed" : status === "warning" ? "Import partially completed" : "Import complete";
  const details = Array.isArray(res.errors)
    ? res.errors.slice(0, 5).map((item: any) => {
        const rowLabel = item.row ? `Row ${item.row}: ` : "";
        const rowErrors = Array.isArray(item.errors) ? item.errors.join(" ") : "Check this row in the source file.";
        return `${rowLabel}${rowErrors}`;
      })
    : [];
  return {
    status,
    details,
    message: `${verb}: ${created} created, ${updated} updated, ${failed} failed.`,
    created,
    updated,
    failed,
  };
}

export function downloadMentorTemplate() {
  downloadApiFile("/admin/mentors/template", "Mentor_Import_Template.xlsx");
}

// ----------------------------------------------------
// MENTOR PORTAL ENDPOINTS
// ----------------------------------------------------

export async function getMentorDashboard(): Promise<MentorDashboardData> {
  return request<MentorDashboardData>("/mentor/dashboard");
}

export async function getMentorStudentsYears(): Promise<MentorYearCardItem[]> {
  return request<MentorYearCardItem[]>("/mentor/students/years");
}

export async function getMentorStudentsSections(year: string): Promise<MentorSectionCardItem[]> {
  return request<MentorSectionCardItem[]>(`/mentor/students/sections?year=${encodeURIComponent(year)}`);
}

export async function getMentorStudents(year?: string, section?: string, search?: string): Promise<StudentItem[]> {
  const params = new URLSearchParams();
  if (year && year !== "ALL") params.append("year", year);
  if (section && section !== "ALL") params.append("section", section);
  if (search) params.append("search", search);
  const qStr = params.toString() ? `?${params.toString()}` : "";
  return request<StudentItem[]>(`/mentor/students${qStr}`);
}

export async function searchMentorStudentsGlobal(query: string): Promise<StudentItem[]> {
  return request<StudentItem[]>(`/mentor/students/search?q=${encodeURIComponent(query)}`);
}

export async function getMentorAbsenteesYears(): Promise<MentorYearCardItem[]> {
  return request<MentorYearCardItem[]>("/mentor/absentees/years");
}

export async function getMentorAbsenteesSections(year: string): Promise<MentorSectionCardItem[]> {
  return request<MentorSectionCardItem[]>(`/mentor/absentees/sections?year=${encodeURIComponent(year)}`);
}

export async function getMentorAbsentees(year: string, section: string, date?: string): Promise<AbsenteeStudentItem[]> {
  const params = new URLSearchParams({ year, section });
  if (date) params.append("date", date);
  return request<AbsenteeStudentItem[]>(`/mentor/absentees?${params.toString()}`);
}

export async function searchMentorAbsenteesGlobal(query: string, date?: string): Promise<AbsenteeStudentItem[]> {
  const params = new URLSearchParams({ q: query });
  if (date) params.append("date", date);
  return request<AbsenteeStudentItem[]>(`/mentor/absentees/search?${params.toString()}`);
}

export async function saveAbsenceComment(recordId: string, comment: string): Promise<AbsenteeStudentItem> {
  return request<AbsenteeStudentItem>(`/mentor/absentees/${recordId}/comment`, {
    method: "PATCH",
    body: JSON.stringify({ comment }),
  });
}
