import { request, downloadApiFile } from "./apiClient";
import type { TimetablePeriod, TimetableUpload } from "@/data/mock/mockData";

export async function getTimetableUploads(): Promise<TimetableUpload[]> {
  const data = await request<any[]>("/admin/timetable");
  const sectionMap = new Map<string, { section: string; year: string; updated_at: string; count: number }>();

  data.forEach((t) => {
    const sec = t.section;
    if (!sec) return;
    const existing = sectionMap.get(sec);
    if (existing) {
      existing.count += 1;
      if (t.updated_at && t.updated_at > existing.updated_at) {
        existing.updated_at = t.updated_at;
      }
    } else {
      sectionMap.set(sec, {
        section: sec,
        year: t.year || "2nd Year",
        updated_at: t.updated_at || "",
        count: 1,
      });
    }
  });

  return Array.from(sectionMap.values()).map((s) => ({
    id: `sec-${s.section}`,
    academicYear: s.year,
    section: s.section,
    file: `${s.section}_Timetable.xlsx`,
    uploadedDate: s.updated_at ? new Date(s.updated_at).toLocaleDateString() : "Today",
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

export async function deleteSectionTimetable(section: string): Promise<void> {
  await request(`/admin/timetable/${encodeURIComponent(section)}`, {
    method: "DELETE",
  });
}

export async function deleteAllTimetables(): Promise<void> {
  await request("/admin/timetable", {
    method: "DELETE",
  });
}
