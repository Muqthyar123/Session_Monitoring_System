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
  return request<CRLRUser[]>("/admin/users?crlr_only=true");
}

export async function createCRLRUser(data: Omit<CRLRUser, "id"> & { password?: string }): Promise<CRLRUser> {
  return request<CRLRUser>("/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateCRLRUser(id: string, data: Omit<CRLRUser, "id"> & { password?: string }): Promise<CRLRUser> {
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

export async function resetCRLRUsers(): Promise<{ message: string; deleted_count?: number }> {
  return request<{ message: string; deleted_count?: number }>("/admin/users/reset", {
    method: "DELETE",
  });
}

export async function uploadCRLRExcel(file: File): Promise<{ message: string; status: "success" | "warning" | "error"; details: string[] }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await request<any>("/admin/users/import", {
    method: "POST",
    body: formData,
  });

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
  };
}

export function downloadCRLRTemplate() {
  downloadApiFile("/admin/users/template", "CR_LR_Import_Template.xlsx");
}
