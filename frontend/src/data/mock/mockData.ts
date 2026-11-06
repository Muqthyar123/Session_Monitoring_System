/** Shared frontend API types. */

export type Role = "SUPER_ADMIN" | "ADMIN" | "CR" | "LR" | "MENTOR" | "DEPARTMENT_COORDINATOR" | "COORDINATOR";
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
  branchId?: string;
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
  created_at?: string;
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


export interface Site {
  id: string;
  code: string;
  name: string;
  location?: string | null;
  address?: string | null;
  contactEmail?: string | null;
  contactPhone?: string | null;
  description?: string | null;
  isActive: boolean;
  branchCount?: number;
  branchesCount?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Branch {
  id: string;
  code: string;
  name: string;
  siteId?: string | null;
  siteName?: string | null;
  siteCode?: string | null;
  hodId?: string | null;
  hodName?: string | null;
  hodEmail?: string | null;
  hodPhone?: string | null;
  description?: string | null;
  isActive: boolean;
  studentCount?: number;
  studentsCount?: number;
  mentorCount?: number;
  mentorsCount?: number;
  sectionCount?: number;
  sectionsCount?: number;
  created_at?: string;
  updated_at?: string;
}

export interface HODItem {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  employeeId?: string | null;
  branchCode?: string | null;
  branchName?: string | null;
  branchId?: string | null;
  role: string;
  designation?: string;
  isActive: boolean;
  studentCount?: number;
  mentorCount?: number;
  created_at?: string;
  updated_at?: string;
}

export interface SuperAdminDashboardData {
  total_branches: number;
  total_sites: number;
  total_hods: number;
  total_mentors: number;
  total_students: number;
  totalBranches?: number;
  totalSites?: number;
  totalHods?: number;
  totalMentors?: number;
  totalStudents?: number;
  branch_stats: Array<{
    id: string;
    code: string;
    name: string;
    site_name: string;
    hod_name: string;
    hod_email: string;
    hod_phone?: string;
    student_count: number;
    mentor_count: number;
    section_count: number;
    is_active: boolean;
  }>;
  recent_branches: Array<{
    id: string;
    code: string;
    name: string;
    site_name: string;
    created_at?: string;
    is_active: boolean;
  }>;
  recent_hods: Array<{
    id: string;
    name: string;
    email: string;
    phone?: string;
    branch_code: string;
    created_at?: string;
    is_active: boolean;
  }>;
}
