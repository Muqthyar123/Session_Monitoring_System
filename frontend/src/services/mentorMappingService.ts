import { request, downloadApiFile } from "./apiClient";

export interface MentorMappingRowItem {
  rowIdx: number;
  mentorName: string;
  mentorId?: string;
  year: string;
  section: string;
  startSerial?: number;
  endSerial?: number;
  isFullSection: boolean;
  status: "VALID" | "ERROR";
  errorMessage?: string;
  studentCount: number;
  matchedStudents: Array<{
    student_id: string;
    roll_number: string;
    name: string;
  }>;
}

export interface MentorMappingPreviewData {
  totalRows: number;
  validRows: number;
  invalidRows: number;
  studentsToAssign: number;
  conflictsCount: number;
  rows: MentorMappingRowItem[];
}

export interface MentorMappingRecord {
  id: string;
  mentorId: string;
  mentorName: string;
  mentorEmail?: string;
  year: string;
  section: string;
  startSerial?: number;
  endSerial?: number;
  isFullSection: boolean;
  studentCount: number;
  studentIds: string[];
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface MentorMappingConfirmPayload {
  mode: "ADD_UPDATE" | "REPLACE";
  rows?: any[];
}

export async function downloadMappingTemplate(): Promise<void> {
  await downloadApiFile(
    "/admin/mentor-student-mapping/template",
    "Mentor_Student_Mapping_Template.xlsx"
  );
}

export async function previewMentorMappings(file: File): Promise<MentorMappingPreviewData> {
  const formData = new FormData();
  formData.append("file", file);
  return request<MentorMappingPreviewData>("/admin/mentor-student-mapping/preview", {
    method: "POST",
    body: formData,
  });
}

export async function confirmMentorMappings(
  payload: MentorMappingConfirmPayload
): Promise<{ success: boolean; message: string; created_count: number; updated_count: number; total_students_assigned: number }> {
  return request<{ success: boolean; message: string; created_count: number; updated_count: number; total_students_assigned: number }>(
    "/admin/mentor-student-mapping/import",
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function getMentorMappings(filters?: {
  year?: string;
  section?: string;
  mentorId?: string;
}): Promise<MentorMappingRecord[]> {
  const params = new URLSearchParams();
  if (filters?.year) params.append("year", filters.year);
  if (filters?.section) params.append("section", filters.section);
  if (filters?.mentorId) params.append("mentor_id", filters.mentorId);

  const queryString = params.toString() ? `?${params.toString()}` : "";
  return request<MentorMappingRecord[]>(`/admin/mentor-student-mapping${queryString}`);
}

export async function deleteMentorMapping(mappingId: string): Promise<void> {
  await request(`/admin/mentor-student-mapping/${mappingId}`, {
    method: "DELETE",
  });
}
