import { request, downloadApiFile } from "./apiClient";
import type { TimetablePeriod, TimetableUpload } from "@/data/mock/mockData";

export async function getTimetableUploads(): Promise<TimetableUpload[]> {
  const data = await request<any[]>("/admin/timetable");
  // Map timetables list summary
  return data.map((t, idx) => ({
    id: t.id || `t-${idx}`,
    academicYear: t.year || "2nd Year",
    section: t.section || "II-A",
    file: `${t.section}_Timetable.xlsx`,
    uploadedDate: t.updated_at ? new Date(t.updated_at).toLocaleDateString() : "Today",
    status: "Processed",
  }));
}

export async function getTimetable(year: string, section: string): Promise<TimetablePeriod[]> {
  const query = year ? `?year=${encodeURIComponent(year)}` : "";
  return request<TimetablePeriod[]>(`/admin/timetable/${encodeURIComponent(section)}${query}`);
}

export async function uploadTimetable(file: File): Promise<{ message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await request<any>("/admin/timetable/upload", {
    method: "POST",
    body: formData,
  });

  return {
    message: res.message || "Timetable workbook processed successfully.",
  };
}

export function downloadTimetableTemplate() {
  downloadApiFile("/admin/timetable/template", "Timetable_Template.xlsx");
}
