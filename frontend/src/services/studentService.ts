import { request, downloadApiFile } from "./apiClient";

export interface StudentItem {
  id: string;
  batch?: string | number;
  branch?: string;
  year: string;
  name: string;
  rollNumber: string;
  section: string;
  studentPhone?: string;
  parentPhone?: string;
  studentEmail?: string;
  serialNumber?: string;
  crlrId?: string;
  crlrName?: string;
}

export interface StudentCreatePayload {
  batch?: string | number;
  branch?: string;
  year?: string;
  name: string;
  rollNumber: string;
  section: string;
  studentPhone?: string;
  parentPhone?: string;
}

export interface StudentPage {
  items: StudentItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StudentFilterOptions {
  years: string[];
  branches: string[];
  sections: string[];
}

export async function getStudentsPage(filters: {
  year?: string; section?: string; search?: string; branch?: string; page: number; pageSize: number;
}): Promise<StudentPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries({ year: filters.year, section: filters.section, search: filters.search, branch: filters.branch })) {
    if (value && value !== "ALL") params.set(key, value);
  }
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  const res = await request<any>(`/admin/students?${params.toString()}`);
  if (Array.isArray(res)) {
    const start = (filters.page - 1) * filters.pageSize;
    return {
      items: res.slice(start, start + filters.pageSize),
      total: res.length,
      page: filters.page,
      page_size: filters.pageSize,
      total_pages: Math.max(1, Math.ceil(res.length / filters.pageSize)),
    };
  }
  if (res && Array.isArray(res.items)) {
    return {
      items: res.items,
      total: typeof res.total === "number" ? res.total : res.items.length,
      page: res.page ?? filters.page,
      page_size: res.page_size ?? filters.pageSize,
      total_pages: res.total_pages ?? Math.max(1, Math.ceil((res.total ?? res.items.length) / filters.pageSize)),
    };
  }
  return {
    items: [],
    total: 0,
    page: filters.page,
    page_size: filters.pageSize,
    total_pages: 1,
  };
}

export async function getStudentFilterOptions(): Promise<StudentFilterOptions> {
  return request<StudentFilterOptions>("/admin/students/filters");
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

export async function resetStudents(): Promise<{ message: string; deleted_count?: number }> {
  return request<{ message: string; deleted_count?: number }>("/admin/students/reset", {
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
