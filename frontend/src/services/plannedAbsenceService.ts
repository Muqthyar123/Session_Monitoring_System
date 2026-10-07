import { request } from "./apiClient";

export interface PlannedAbsenceItem {
  id: string;
  studentId: string;
  studentName: string;
  rollNumber: string;
  year: string;
  section: string;
  startDate: string;
  endDate: string;
  reason: string;
  status: "ACTIVE" | "CANCELLED" | "COMPLETED";
  mentorId?: string;
  mentorName?: string;
  createdByRole?: string;
  cancelledBy?: string;
  cancelledAt?: string;
  cancellationReason?: string;
  createdAt?: string;
  updatedAt?: string;
  isActiveToday?: boolean;
}

export interface PlannedAbsenceCreatePayload {
  studentId?: string;
  studentName?: string;
  rollNumber: string;
  year?: string;
  section?: string;
  startDate: string;
  endDate: string;
  reason: string;
}

export interface PlannedAbsenceUpdatePayload {
  startDate?: string;
  endDate?: string;
  reason?: string;
}

export interface PlannedAbsenceCancelPayload {
  cancellationReason: string;
}

export interface PlannedAbsenceFilters {
  studentId?: string;
  rollNumber?: string;
  year?: string;
  section?: string;
  status?: string;
  activeOnly?: boolean;
}

export async function createPlannedAbsence(
  payload: PlannedAbsenceCreatePayload
): Promise<PlannedAbsenceItem> {
  return request<PlannedAbsenceItem>("/mentor/planned-absences", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPlannedAbsences(
  filters: PlannedAbsenceFilters = {}
): Promise<PlannedAbsenceItem[]> {
  const params = new URLSearchParams();
  if (filters.studentId) params.append("student_id", filters.studentId);
  if (filters.rollNumber) params.append("roll_number", filters.rollNumber);
  if (filters.year) params.append("year", filters.year);
  if (filters.section) params.append("section", filters.section);
  if (filters.status) params.append("status", filters.status);
  if (filters.activeOnly) params.append("activeOnly", "true");

  const queryString = params.toString() ? `?${params.toString()}` : "";
  return request<PlannedAbsenceItem[]>(`/mentor/planned-absences${queryString}`);
}

export async function updatePlannedAbsence(
  id: string,
  payload: PlannedAbsenceUpdatePayload
): Promise<PlannedAbsenceItem> {
  return request<PlannedAbsenceItem>(`/mentor/planned-absences/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function cancelPlannedAbsence(
  id: string,
  payload: PlannedAbsenceCancelPayload
): Promise<PlannedAbsenceItem> {
  return request<PlannedAbsenceItem>(`/mentor/planned-absences/${id}/cancel`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAdminPlannedAbsences(
  filters: PlannedAbsenceFilters = {}
): Promise<PlannedAbsenceItem[]> {
  const params = new URLSearchParams();
  if (filters.studentId) params.append("student_id", filters.studentId);
  if (filters.rollNumber) params.append("roll_number", filters.rollNumber);
  if (filters.year) params.append("year", filters.year);
  if (filters.section) params.append("section", filters.section);
  if (filters.status) params.append("status", filters.status);
  if (filters.activeOnly) params.append("activeOnly", "true");

  const queryString = params.toString() ? `?${params.toString()}` : "";
  return request<PlannedAbsenceItem[]>(`/admin/planned-absences${queryString}`);
}
