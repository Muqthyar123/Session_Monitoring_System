import { request, downloadApiFile } from "./apiClient";
import type { CRLRUser } from "@/data/mock/mockData";

export interface SectionItem {
  id: string;
  year: string;
  section_name: string;
  department?: string;
  assigned_cr_id?: string;
  assigned_lr_id?: string;
  cr_name?: string;
  lr_name?: string;
}

export async function getSections(): Promise<SectionItem[]> {
  return request<SectionItem[]>("/sections");
}

export async function getCRLRUsers(): Promise<CRLRUser[]> {
  return request<CRLRUser[]>("/admin/users");
}

export async function createCRLRUser(data: Omit<CRLRUser, "id">): Promise<CRLRUser> {
  return request<CRLRUser>("/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateCRLRUser(id: string, data: Omit<CRLRUser, "id">): Promise<CRLRUser> {
  return request<CRLRUser>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteCRLRUser(id: string): Promise<void> {
  return request<void>(`/admin/users/${id}`, {
    method: "DELETE",
  });
}

export async function uploadCRLRExcel(file: File): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await request<any>("/admin/users/import", {
    method: "POST",
    body: formData,
  });

  return {
    message: res.message || `Import completed successfully: ${res.created} users created, ${res.updated} updated.`,
  };
}

export function downloadCRLRTemplate() {
  downloadApiFile("/admin/users/template", "CR_LR_Import_Template.xlsx");
}
