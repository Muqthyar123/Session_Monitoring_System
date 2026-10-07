# College Session Monitoring System — Frontend Application

Production-ready **React 19 + TypeScript** frontend for the **College Faculty & Student Session Monitoring System**, fully integrated with the **Python FastAPI Backend** and **MongoDB Atlas**.

---

## 🚀 Tech Stack & Core Libraries

- **Framework**: React 19 + TypeScript
- **Bundler & Build Tool**: Vite v8 + Nitro
- **Routing**: TanStack Router (Type-safe, file-based routing)
- **Styling**: Tailwind CSS v4 + shadcn/ui component primitives
- **Icons**: Lucide React
- **Charts & Visualizations**: Recharts
- **Toast Notifications**: Sonner
- **Data Exporting**: Custom CSV/Excel exporter with header transformations
- **HTTP Client**: Centralized Fetch API Client with automatic JWT Bearer authentication interceptor and binary file download handler

---

## 🔑 Role Login Credentials & Portals

| Role | Portal Login URL | Default Identifier / Email | Default Password | Monitored Scope |
|---|---|---|---|---|
| **ADMIN** | `/admin/login` | `admin@example.com` | `demo1234` | System-wide Administrative Management |
| **MENTOR** | `/mentor/login` | `605101` (or `mentor@example.com`) | `demo1234` | Assigned Students & Sections |
| **CR** | `/auth/login` | `cr@example.com` | `demo1234` | Assigned Section (`II-A` / `2nd Year`) |
| **LR** | `/auth/login` | `lr@example.com` | `demo1234` | Assigned Section (`II-A` / `2nd Year`) |

---

## 🗺️ Application Route Structure

### 1. Root & Authentication Routes
```text
/                      Portal Directory Landing (Admin / CR-LR / Mentor)
/auth/login            Student Representative (CR / LR) Login
/admin/login           System Administrator Login
/mentor/login          Faculty Mentor Login
```

### 2. Admin Portal Routes (`/admin/*`)
```text
/admin/dashboard            Executive Dashboard (Live Atlas metrics, quick actions & system summary)
/admin/analytics            Faculty Analytics (Attendance rates, department breakdowns & session logs)
/admin/student-analytics    Student Analytics (Section attendance percentages & frequent absentees)
/admin/student-history      Student History (Longitudinal attendance search, date filters & audit records)
/admin/departments          Department Management (Add, view, edit & deactivate academic branches)
/admin/sections             Academic Sections (Add sections dynamically per year & department)
/admin/mentors              Manage Mentors (CRUD faculty mentors, contact details & Excel bulk import)
/admin/mentor-mapping       Mentor-Student Mapping (Excel import, serial range assignments & conflict preview)
/admin/students             Manage Students (CRUD students, roll number indexing & Excel import)
/admin/timetable            Timetable Management (Multi-sheet workbook upload, templates & schedule viewer)
/admin/cr-lr                CR/LR Management (Manual creation & Excel import of student representatives)
/admin/sessions             Session Monitoring (Continuous teaching sessions, active periods & lab merging)
/admin/alerts               Notifications & Alerts (Immediate absence escalations & 10-min timeout alerts)
```

### 3. CR / LR Representative Portal Routes (`/crlr/*`)
```text
/crlr/dashboard             CR/LR Dashboard (Current continuous session & quick presence reporting)
/crlr/attendance            Faculty Presence Response (Hourly presence deadline & lab merging)
/crlr/student-attendance    Daily Student Attendance (Single submission per day with phone numbers)
                            + Attendance Correction (Correct absent student to PRESENT with audit reason)
/crlr/timetable             Class Timetable (Assigned section's weekly period schedule)
/crlr/analytics             Section Attendance Trends & Weekly Analytics
/crlr/notifications         In-App Notifications (Session start alerts & read/unread tracking)
```

### 4. Faculty Mentor Portal Routes (`/mentor/*`)
```text
/mentor/dashboard           Mentor Dashboard (Assigned student metrics, today's absentees & monitored years)
/mentor/students            Enrolled Students Directory (Scoped assigned students, contact info & leave status)
/mentor/absentees           Today's Absentees (Section-wise absentee lists, phone dialers, reason notes & CSV export)
/mentor/planned-absences    Student Planned Absence Management (Record approved date ranges, edit & cancel)
/mentor/analytics           Attendance Analytics (Longitudinal attendance percentages & frequent absentee tracking)
```

---

## 📁 Frontend Directory Architecture

```text
frontend/src/
├── components/
│   ├── common/              # Reusable UI widgets:
│   │   ├── DataTable.tsx    # Paginated data table with sorting and customizable column cells
│   │   ├── StatCard.tsx     # KPI summary card with trend tones and icons
│   │   ├── PageHeader.tsx   # Consistent top banner with breadcrumbs and action buttons
│   │   ├── FileUpload.tsx   # Drag-and-drop Excel file uploader with validation
│   │   ├── RoleGuard.tsx    # Client-side RBAC route protector
│   │   └── States.tsx       # LoadingState, EmptyState, and ErrorState components
│   ├── sessions/            # Attendance forms, hourly timer countdown & response windows
│   ├── notifications/       # NotificationBell with unread badges
│   └── ui/                  # Accessible UI primitives (Button, Card, Dialog, Select, Badge, Table, Input)
├── layouts/
│   ├── AdminLayout.tsx      # Admin portal left sidebar navigation with active route highlights
│   ├── CRLRLayout.tsx       # CR/LR mobile-responsive navigation wrapper
│   └── MentorLayout.tsx     # Mentor portal navigation wrapper
├── routes/                  # TanStack Router file-based route definitions
├── services/                # Backend API service integration layer:
│   ├── apiClient.ts         # Centralized Fetch client with JWT interceptor & binary download handler
│   ├── authService.ts       # Authentication, login state & user profile storage
│   ├── mentorMappingService.ts # Excel template download, preview parsing, mapping commit & delete
│   ├── plannedAbsenceService.ts # Planned absence CRUD, date filters & active state lookups
│   ├── mentorService.ts     # Mentor dashboard, scoped students, absentees & follow-up notes
│   ├── studentService.ts    # Student management, search, year/batch inference & Excel import
│   ├── studentAttendanceService.ts # Daily attendance submission & audit-logged correction
│   ├── sectionService.ts    # Dynamic section management per year and branch
│   ├── departmentService.ts # Academic department management
│   ├── timetableService.ts  # Timetable upload, section timetable retrieval & templates
│   ├── sessionService.ts    # Continuous session engine viewer & faculty presence submitter
│   ├── notificationService.ts # In-app notifications & unread counter
│   └── analyticsService.ts  # Faculty and student analytics aggregations
├── hooks/
│   ├── useAsyncData.ts      # Automatic loading/error state handler with polling support
│   └── useAuth.ts           # Authentication context hook
├── utils/
│   └── exportUtils.ts       # Universal CSV/Excel exporter with header transformers
└── lib/
    └── utils.ts             # Tailwind class merging utility (`cn`)
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 💻 Development & Build Commands

```bash
# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev

# 3. Build for production (TypeScript check & bundling)
npm run build

# 4. Preview production build locally
npm run preview
```

- **Local Development URL**: `http://localhost:5173`
- **FastAPI Backend URL**: `http://localhost:8000`
