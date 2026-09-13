# College Faculty Attendance & Session Monitoring System — Frontend

Production-ready **React + TypeScript** frontend for the **College Faculty Attendance & Session Monitoring System**, fully integrated with the **Python FastAPI Backend** and **MongoDB Atlas**.

---

## 🚀 Tech Stack

- **Framework**: React 19 + TypeScript
- **Routing**: TanStack Router (File-based routing)
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Icons**: Lucide React
- **Charts**: Recharts
- **HTTP Client**: Centralized Fetch API Client with JWT Bearer Authentication

---

## 🔑 Login Credentials

| Role | Login Portal | Email | Password | Section / Scope |
| --- | --- | --- | --- | --- |
| **ADMIN** | `/admin/login` | `admin@example.com` | `demo1234` | System-wide Administration |
| **CR** | `/auth/login` | `cr@example.com` | `demo1234` | Assigned Section (`II-A`) |
| **LR** | `/auth/login` | `lr@example.com` | `demo1234` | Assigned Section (`II-A`) |

---

## 🗺️ Application Routes

```text
/                      Portal Selection (Admin / CR / LR)
/admin/login           Administrator Login
/admin/dashboard       Admin Dashboard (Live Atlas Analytics + System Summary)
/admin/timetable       Timetable Management (Excel upload, template download, section timetables)
/admin/cr-lr           CR/LR Management (Manual CRUD + Excel workbook import)
/admin/sessions        Session Monitoring (Active, upcoming & completed continuous sessions)
/admin/alerts          Admin Attendance Alerts (Immediate absence & 10-min escalation alerts)

/auth/login            CR / LR Student Representative Login
/crlr/dashboard        CR/LR Dashboard (Assigned section overview & active session)
/crlr/attendance       Faculty Attendance Response (PRESENT, ABSENT, SUBSTITUTE reporting)
/crlr/analytics        Section Attendance Analytics & Weekly Trends
/crlr/notifications    Notification Panel (Unread counts & mark read status)
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the `frontend` root directory:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 📁 Project Architecture

```text
frontend/src/
├── components/
│   ├── common/        # StatCard, StatusBadge, DataTable, FileUpload, Loading/Error States, RoleGuard
│   ├── sessions/      # AttendanceForm (PRESENT/ABSENT/SUBSTITUTE), ResponseWindow Countdown
│   ├── notifications/ # NotificationBell with unread counter
│   └── ui/            # shadcn/ui component primitives
├── layouts/           # AdminLayout & CRLRLayout navigation wrappers
├── routes/            # File-based TanStack routes
├── services/          # Real API Integration Layer (FastAPI REST Backend)
│   ├── apiClient.ts   # Centralized HTTP request client & JWT bearer token interceptor
│   ├── authService.ts # Login, logout, JWT persistence & profile fetching
│   ├── userService.ts # CR/LR CRUD, section lookup, Excel import & template download
│   ├── timetableService.ts # Timetable upload, section timetable retrieval & template download
│   ├── sessionService.ts   # Session retrieval, attendance submission & admin alerts
│   └── notificationService.ts # In-app notifications & read status updates
└── data/mock/         # TypeScript DTO interfaces & type definitions
```

---

## 🌐 FastAPI Backend Integration

All frontend service calls (`src/services/*`) interact directly with the FastAPI REST API backend:

1. **Authentication**: Sends credentials to `/api/auth/login`, receives a signed JWT access token, and automatically attaches `Authorization: Bearer <token>` to all protected API calls.
2. **Role & Section Authorization**: Client UI uses `RoleGuard.tsx` for navigation protection, while the backend strictly enforces role-based and section-based access control.
3. **Continuous Session Display**: Renders continuous class sessions (e.g. 09:10–11:40 DBMS) calculated by the backend session engine.
4. **Attendance Submission**: Submits `PRESENT`, `ABSENT`, or `SUBSTITUTE` with required substitute name validation. Triggers immediate Admin Alerts for absences.
5. **Excel Workbooks**: Uploads `.xlsx` files using `multipart/form-data` and downloads binary template workbooks directly from backend API endpoints.

---

## 💻 Development Setup & Running

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Start the Vite development server
npm run dev
```

- **Frontend Application URL**: `http://localhost:5173`
- **FastAPI Backend URL**: `http://localhost:8000`
