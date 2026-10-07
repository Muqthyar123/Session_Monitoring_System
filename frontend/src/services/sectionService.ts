import { request } from "./apiClient";

export interface Section {
  id: string;
  year: string;
  branch: string;
  department: string;
  sectionName: string;
  assignedCrId?: string | null;
  assignedLrId?: string | null;
  crName?: string | null;
  lrName?: string | null;
  studentCount: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SectionCreate {
  year: string;
  branch: string;
  sectionName: string;
  assignedCrId?: string | null;
  assignedLrId?: string | null;
  isActive?: boolean;
}

export interface SectionUpdate {
  year?: string;
  branch?: string;
  sectionName?: string;
  assignedCrId?: string | null;
  assignedLrId?: string | null;
  isActive?: boolean;
}

export async function getSections(year?: string, branch?: string, isActive?: boolean): Promise<Section[]> {
  const params = new URLSearchParams();
  if (year && year !== "ALL") params.append("year", year);
  if (branch && branch !== "ALL") params.append("branch", branch);
  if (isActive !== undefined) params.append("is_active", String(isActive));

  const qs = params.toString();
  return request<Section[]>(`/sections${qs ? `?${qs}` : ""}`);
}

export async function createSection(data: SectionCreate): Promise<Section> {
  return request<Section>("/sections", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSection(id: string, data: SectionUpdate): Promise<Section> {
  return request<Section>(`/sections/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSection(id: string): Promise<{ id: string; action: string }> {
  return request<{ id: string; action: string }>(`/sections/${id}`, {
    method: "DELETE",
  });
}
