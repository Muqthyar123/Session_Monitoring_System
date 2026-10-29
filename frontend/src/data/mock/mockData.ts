/** Shared frontend API types. */

export type Role = "ADMIN" | "CR" | "LR" | "MENTOR" | "DEPARTMENT_COORDINATOR" | "COORDINATOR";
export type SessionStatus = "Upcoming" | "Active" | "Completed" | "Expired";
export type FacultyResponse = "Pending" | "Present" | "Not Present" | "Substitute" | "CR/LR Not Marked";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  year?: string;
  section?: string;
  department?: string;
  branch?: string;
  mentorId?: string;
}

export interface CRLRUser {
  id: string;
  name: string;
  rollNumber: string;
  email: string;
  role: "CR" | "LR";
  year: string;
  section: string;
}

export interface TimetableUpload {
  id: string;
  academicYear: string;
  section: string;
  file: string;
  uploadedDate: string;
  status: "Processed" | "Processing" | "Failed";
}

export interface TimetablePeriod {
  id?: string;
  year?: string;
  section?: string;
  day: string;
  period: number;
  startTime: string;
  endTime: string;
  subject: string;
  faculty?: string;
  facultyNames?: string[];
  room?: string;
}

export interface ClassSession {
  id: string;
  _id?: string;
  section: string;
  year?: string;
  subject: string;
  faculty?: string;
  facultyNames?: string[];
  period: string;
  periodsIncluded: number[];
  startTime: string;
  endTime: string;
  date: string;
  crlrName: string;
  crlrRole: "CR" | "LR";
  sessionStatus: SessionStatus;
  facultyResponse: FacultyResponse;
  responseTime: string | null;
  substituteName: string | null;
  submittedByName?: string | null;
  submittedRole?: string | null;
  /** Provided by the backend. Frontend only displays it. */
  responseWindowSecondsRemaining: number | null;
  responseWindowExpired: boolean;
}

export interface AdminAlert {
  id: string;
  section: string;
  subject: string;
  session: string;
  time: string;
  reportedBy: "CR" | "LR";
  reason: "Faculty not available" | "No response within 10 minutes";
  status: "New" | "Acknowledged";
}

export interface AppNotification {
  id: string;
  title: string;
  section: string;
  subject: string;
  time: string;
  message: string;
  read: boolean;
  sessionId: string | null;
}

