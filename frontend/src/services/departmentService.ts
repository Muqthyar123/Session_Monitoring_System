import { request } from "./apiClient";

export interface Department {
  id: string;
  code: string;
  name: string;
  coordinatorId?: string | null;
  coordinatorName?: string | null;
  coordinatorEmail?: string | null;
  isActive: boolean;
  branchId?: string | null;
  branchCode?: string | null;
  branchName?: string | null;
  academicYears?: string[];
  /** Legacy FastAPI responses may expose the Mongo field without its alias. */
  academic_years?: string[];
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
  branchId?: string;
  branchCode?: string;
  academicYears?: string[];
}

export interface DepartmentUpdate {
  code?: string;
  name?: string;
  coordinatorId?: string | null;
  coordinatorName?: string | null;
  coordinatorEmail?: string | null;
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
