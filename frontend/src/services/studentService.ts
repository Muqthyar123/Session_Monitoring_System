import { request, downloadApiFile } from "./apiClient";

export interface StudentItem {
  id: string;
  year: string;
  name: string;
  rollNumber: string;
  section: string;
  studentPhone?: string;
  parentPhone?: string;
}

export interface StudentCreatePayload {
  year: string;
  name: string;
  rollNumber: string;
  section: string;
  studentPhone?: string;
  parentPhone?: string;
}

export async function getStudents(year?: string, section?: string, search?: string): Promise<StudentItem[]> {
  const params = new URLSearchParams();
  if (year && year !== "ALL") params.append("year", year);
  if (section && section !== "ALL") params.append("section", section);
  if (search) params.append("search", search);

  const query = params.toString() ? `?${params.toString()}` : "";
  return request<StudentItem[]>(`/admin/students${query}`);
}

export async function createStudent(data: StudentCreatePayload): Promise<StudentItem> {
  return request<StudentItem>("/admin/students", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateStudent(id: string, data: Partial<StudentCreatePayload>): Promise<StudentItem> {
  return request<StudentItem>(`/admin/students/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteStudent(id: string): Promise<void> {
  return request<void>(`/admin/students/${id}`, {
    method: "DELETE",
  });
}

export async function uploadStudentExcel(file: File): Promise<{ message: string; created?: number; failed?: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await request<any>("/admin/students/import", {
    method: "POST",
    body: formData,
  });

  return {
    message: res.message || `Import complete: ${res.created} created, ${res.updated} updated.`,
    created: res.created,
    failed: res.failed,
  };
}

export function downloadStudentTemplate() {
  downloadApiFile("/admin/students/template", "Student_Import_Template.xlsx");
}
