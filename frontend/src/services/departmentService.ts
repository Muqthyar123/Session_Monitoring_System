import { request } from "./apiClient";

export interface Department {
  id: string;
  code: string;
  name: string;
  coordinatorId?: string | null;
  coordinatorName?: string | null;
  coordinatorEmail?: string | null;
  isActive: boolean;
  studentCount: number;
  sectionCount: number;
  facultyCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface DepartmentCreate {
  code: string;
  name: string;
  coordinatorId?: string | null;
  coordinatorName?: string | null;
  coordinatorEmail?: string | null;
  isActive?: boolean;
}

export interface DepartmentUpdate {
  code?: string;
  name?: string;
  coordinatorId?: string | null;
  isActive?: boolean;
}

export async function getDepartments(): Promise<Department[]> {
  return request<Department[]>("/admin/departments");
}

export async function createDepartment(data: DepartmentCreate): Promise<Department> {
  return request<Department>("/admin/departments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDepartment(id: string, data: DepartmentUpdate): Promise<Department> {
  return request<Department>(`/admin/departments/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteDepartment(id: string): Promise<{ id: string; action: string }> {
  return request<{ id: string; action: string }>(`/admin/departments/${id}`, {
    method: "DELETE",
  });
}
