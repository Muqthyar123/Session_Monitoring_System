import { request, uploadRequest, downloadApiFile } from "./apiClient";
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

export async function uploadTimetable(file: File, onProgress?: (percent: number) => void): Promise<{ message: string; status: "success" | "warning" | "error"; details: string[]; inserted: number; updated: number; failed: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await uploadRequest<any>("/admin/timetable/upload", formData, onProgress);

  const inserted = Number(res.inserted ?? 0);
  const updated = Number(res.updated ?? 0);
  const failed = Number(res.failed ?? 0);
  const changed = inserted + updated;
  const status = failed === 0 ? "success" : changed > 0 ? "warning" : "error";
  const verb = status === "error" ? "Import failed" : status === "warning" ? "Import partially completed" : "Import complete";
  const details = Array.isArray(res.errors)
    ? res.errors.slice(0, 5).map((item: any) => {
        const location = [item.sheet, item.row ? `row ${item.row}` : null].filter(Boolean).join(" ");
        return `${location ? `${location}: ` : ""}${Array.isArray(item.errors) ? item.errors.join(" ") : "Check this timetable entry."}`;
      })
    : [];
  return { message: `${verb}: ${inserted} inserted, ${updated} updated, ${Number(res.unchanged ?? 0)} unchanged, ${failed} failed.`, status, details, inserted, updated, failed };
}

export function downloadTimetableTemplate() {
  downloadApiFile("/admin/timetable/template", "Timetable_Template.xlsx");
}

export async function deleteSectionTimetable(section: string): Promise<void> {
  await request(`/admin/timetable/${encodeURIComponent(section)}`, {
    method: "DELETE",
  });
}

export async function deleteAllTimetables(): Promise<{ message?: string; timetables_deleted?: number; sessions_deleted?: number; attendance_records_deleted?: number }> {
  return request("/admin/timetable", {
    method: "DELETE",
  });
}

export async function resetAllTimetables(): Promise<{ message?: string; timetables_deleted?: number; sessions_deleted?: number; attendance_records_deleted?: number }> {
  return request("/admin/timetable/reset", {
    method: "POST",
  });
}
