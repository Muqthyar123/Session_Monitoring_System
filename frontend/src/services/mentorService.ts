import { request, downloadApiFile } from "./apiClient";

export interface MentorItem {
  id: string;
  name: string;
  mentorId: string;
  email: string;
  phone?: string;
  role: "MENTOR";
  createdAt?: string;
}

export interface MentorCreatePayload {
  name: string;
  mentorId: string;
  email?: string;
  password?: string;
  phone?: string;
}

export interface MentorUpdatePayload {
  name?: string;
  mentorId?: string;
  email?: string;
  password?: string;
  phone?: string;
}

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

export async function uploadMentorExcel(file: File): Promise<{ message: string; created?: number; failed?: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await request<any>("/admin/mentors/import", {
    method: "POST",
    body: formData,
  });

  return {
    message: res.message || `Import complete: ${res.created} created, ${res.updated} updated.`,
    created: res.created,
    failed: res.failed,
  };
}

export function downloadMentorTemplate() {
  downloadApiFile("/admin/mentors/template", "Mentor_Import_Template.xlsx");
}
