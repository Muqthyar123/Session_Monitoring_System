import { request } from "./apiClient";
import type {
  Site,
  Branch,
  HODItem,
  SuperAdminDashboardData,
} from "@/data/mock/mockData";

// =====================================================================
// Dashboard
// =====================================================================
export async function getSuperAdminDashboard(): Promise<SuperAdminDashboardData> {
  return request<SuperAdminDashboardData>("/super-admin/dashboard");
}

// =====================================================================
// Sites Management
// =====================================================================
export async function getSites(): Promise<Site[]> {
  return request<Site[]>("/super-admin/sites");
}

export async function createSite(data: {
  code: string;
  name: string;
  location?: string | undefined;
  address?: string | undefined;
  contactEmail?: string | undefined;
  contactPhone?: string | undefined;
  description?: string | undefined;
  isActive?: boolean | undefined;
}): Promise<Site> {
  return request<Site>("/super-admin/sites", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSite(
  siteId: string,
  data: Partial<Site>
): Promise<Site> {
  return request<Site>(`/super-admin/sites/${siteId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSite(siteId: string, force = false): Promise<any> {
  return request<any>(`/super-admin/sites/${siteId}?force=${force}`, {
    method: "DELETE",
  });
}

// =====================================================================
// Branches Management
// =====================================================================
export async function getBranches(params?: {
  search?: string;
  site_id?: string;
  is_active?: boolean;
}): Promise<Branch[]> {
  const query = new URLSearchParams();
  if (params?.search) query.append("search", params.search);
  if (params?.site_id) query.append("site_id", params.site_id);
  if (params?.is_active !== undefined) query.append("is_active", String(params.is_active));

  const qs = query.toString();
  return request<Branch[]>(`/super-admin/branches${qs ? `?${qs}` : ""}`);
}

export async function getBranch(branchId: string): Promise<Branch> {
  return request<Branch>(`/super-admin/branches/${branchId}`);
}

export async function createBranch(data: {
  code: string;
  name: string;
  siteId?: string | undefined;
  siteName?: string | undefined;
  siteCode?: string | undefined;
  hodId?: string | undefined;
  description?: string | undefined;
  isActive?: boolean | undefined;
}): Promise<Branch> {
  return request<Branch>("/super-admin/branches", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateBranch(
  branchId: string,
  data: {
    code?: string | undefined;
    name?: string | undefined;
    siteId?: string | undefined;
    siteName?: string | undefined;
    siteCode?: string | undefined;
    hodId?: string | undefined;
    description?: string | undefined;
    isActive?: boolean | undefined;
  }
): Promise<Branch> {
  return request<Branch>(`/super-admin/branches/${branchId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteBranch(
  branchId: string,
  force = false
): Promise<any> {
  return request<any>(`/super-admin/branches/${branchId}?force=${force}`, {
    method: "DELETE",
  });
}

// =====================================================================
// HOD Management
// =====================================================================
export async function getHods(params?: {
  search?: string;
  branch_code?: string;
}): Promise<HODItem[]> {
  const query = new URLSearchParams();
  if (params?.search) query.append("search", params.search);
  if (params?.branch_code) query.append("branch_code", params.branch_code);

  const qs = query.toString();
  return request<HODItem[]>(`/super-admin/hods${qs ? `?${qs}` : ""}`);
}

export async function getHod(hodId: string): Promise<HODItem> {
  return request<HODItem>(`/super-admin/hods/${hodId}`);
}

export async function createHod(data: {
  name: string;
  email: string;
  phone?: string | undefined;
  branchCode: string;
  branchId?: string | undefined;
  password?: string | undefined;
  isActive?: boolean | undefined;
}): Promise<HODItem> {
  return request<HODItem>("/super-admin/hods", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateHod(
  hodId: string,
  data: {
    name?: string | undefined;
    email?: string | undefined;
    phone?: string | undefined;
    branchCode?: string | undefined;
    branchId?: string | undefined;
    password?: string | undefined;
    isActive?: boolean | undefined;
  }
): Promise<HODItem> {
  return request<HODItem>(`/super-admin/hods/${hodId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function resetHodPassword(
  hodId: string,
  newPassword: string
): Promise<any> {
  return request<any>(`/super-admin/hods/${hodId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ newPassword }),
  });
}

export async function toggleHodStatus(hodId: string): Promise<any> {
  return request<any>(`/super-admin/hods/${hodId}/toggle-status`, {
    method: "PATCH",
  });
}

export async function deleteHod(hodId: string): Promise<any> {
  return request<any>(`/super-admin/hods/${hodId}`, {
    method: "DELETE",
  });
}
