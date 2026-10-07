# College Faculty & Student Session Monitoring System

A production-grade, full-stack academic monitoring web application designed for engineering colleges to automate faculty session tracking, hourly presence deadlines, lab session merging, student daily attendance, controlled attendance corrections, mentor planned absence management, mentor-to-student bulk mappings, and administrative analytics.

Built with a **React 19 + TypeScript + Tailwind CSS** frontend, a **Python FastAPI** REST API backend with strict server-side RBAC, and **MongoDB Atlas** cloud database storage.

---

## 🌟 System Overview & Key Portals

### 1. 🛡️ Admin Portal (`/admin/*`)
- **System-Wide Dashboard**: Live metrics, total students, active faculty, today's absentees, and real-time alerts.
- **Faculty Analytics & Session Monitoring**: Continuous lecture session tracking, substitute faculty reporting, and multi-period lab session auto-merging.
- **Student Analytics & Student History**: Longitudinal attendance tracking, percentage calculations, date-range filtering, and student audit history.
- **Academic Structure Management**:
  - **Departments**: Create, edit, and manage engineering departments/branches (e.g. CSE, ECE, EEE, MECH, CIVIL, IT).
  - **Manage Sections**: Add, view, filter, and deactivate sections dynamically per academic year and branch (e.g., 2nd Year CSE-A, 3rd Year ECE-B).
- **Stakeholder Management**:
  - **Manage Mentors**: CRUD mentor accounts, phone/email contact info, designations, and Excel bulk imports.
  - **Mentor-Student Mapping**: Bulk map mentors to entire sections or specific roll-number serial ranges (e.g. S.No 1 to 30) via Excel upload with dry-run validation preview and merge/replace modes.
  - **Manage Students**: Student enrollment, roll number indexing, batch inference, section assignment, and Excel import.
  - **CR/LR Management**: Class Representative (CR) & Lady Representative (LR) user management, section bindings, and credentials.
- **Timetable Management**: Multi-sheet timetable uploads (`.xlsx`/`.xls`), automated continuous session generation, period timing configs, and reset utilities.
- **Notifications & Escalation Alerts**: Real-time faculty absence alerts, 10-minute timeout escalations, and audit logs.

### 2. 🎓 CR / LR Representative Portal (`/crlr/*` & `/auth/*`)
- **Hourly Faculty Presence Window**: CR/LR updates faculty presence within the scheduled class hour. If unsubmitted by the end of the hour, the backend automatically marks faculty absent.
- **Multi-Period Lab Session Auto-Merging**: Consecutive lab periods (e.g. Periods 4, 5, 6 Programming Lab) are automatically consolidated into a single actionable session card.
- **Daily Student Attendance**: Single-submission daily absentee recording for the assigned section with phone numbers for students and parents.
- **Controlled Attendance Corrections**: CR/LR can correct an absent student to PRESENT on the same day with a mandatory audit reason (minimum 5 characters).
- **Class Timetable & In-App Notifications**: Real-time period schedule viewing and start-of-class notification alerts.

### 3. 👨‍🏫 Mentor Portal (`/mentor/*`)
- **Scoped Mentor Access (Strict RBAC)**: Mentors can only view and manage students explicitly assigned to them via Admin Mentor Mapping.
- **Mentor Dashboard**: Overview cards showing assigned student totals, today's absentees, and monitored academic years/sections.
- **Enrolled Students Directory**: Scoped directory of assigned students with contact details, batch/year inference, and active leave indicators.
- **Today's Absentees & Dialer Actions**: Section-wise absentee rosters with one-click direct phone dialers (`tel:`) for students and parents, follow-up comment notes, and CSV/Excel exports.
- **Student Planned Absence Management**:
  - Schedule approved absence periods (`start_date` to `end_date`) with mandatory reasons (Medical leave, OD, Sports event, Family emergency).
  - Server-side date range validation and overlap prevention.
  - Dynamic active status computation in IST (`Asia/Kolkata`).
  - Active planned absence badges on absentee rosters that suppress unnecessary repetitive daily contact prompts.
  - Complete edit and cancellation lifecycle with audit logging.
- **Attendance Analytics**: Longitudinal attendance percentages and frequent absentee tracking.

---

## 🏗️ Technology Stack

### Frontend
- **Framework**: React 19 + TypeScript
- **Routing**: TanStack Router (File-based routing)
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Charts & Data Viz**: Recharts
- **Icons**: Lucide React
- **Notifications & Toasts**: Sonner
- **HTTP Client**: Centralized Fetch API client with automatic JWT Bearer authentication interceptor and binary file download handler

### Backend
- **Framework**: Python 3.13 / FastAPI (Asynchronous ASGI)
- **Database**: MongoDB Atlas via `motor` async driver
- **Authentication**: JWT (`pyjwt`) with `bcrypt` password hashing and role-based security dependencies
- **Timezone**: `Asia/Kolkata` (`UTC+05:30`)
- **Background Scheduler**: `APScheduler` (AsyncIOScheduler) for automatic absence fallback and escalation triggers
- **Spreadsheet Processing**: `openpyxl`, `pandas`
- **Automated Testing**: `pytest`, `pytest-asyncio`, `httpx`, `mongomock-motor`

---

## 📂 Repository Directory Structure

```text
Session_Monitoring_System/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, users, mentors, mentor_mapping, planned_absence,
│   │   │                 #                  departments, mentor, students, sections, timetable,
│   │   │                 #                  sessions, attendance, student_attendance, notifications, analytics)
│   │   ├── core/         # Config, security utilities, JWT handler & RBAC dependencies
│   │   ├── db/           # MongoDB motor async connection, lifecycle & index configurations
│   │   ├── models/       # Database document specifications
│   │   ├── schemas/      # Pydantic v2 schemas and validation DTOs
│   │   ├── services/     # Business logic, Excel parsers, session engine, mentor mapping & planned absences
│   │   └── scheduler/    # APScheduler background tasks
│   ├── scripts/          # Database seeding scripts (seed_db.py)
│   ├── tests/            # Automated pytest suite (35 comprehensive unit/integration tests)
│   ├── .env.example      # Backend environment configuration template
│   ├── pytest.ini        # Pytest configuration
│   └── requirements.txt  # Python package dependencies
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components (DataTable, StatCard, FileUpload, StatusBadge, Dialogs)
│   │   ├── layouts/      # AdminLayout, CRLRLayout & MentorLayout wrappers
│   │   ├── routes/       # TanStack file-based routes
│   │   ├── services/     # API service integrations (FastAPI client)
│   │   ├── hooks/        # Reusable React hooks (useAsyncData, useAuth)
│   │   └── lib/          # Helper utilities (exportUtils, cn)
│   ├── .env.example      # Frontend environment template
│   ├── package.json      # NPM package dependencies
│   ├── vite.config.ts    # Vite bundler configuration
│   └── README.md         # Frontend technical guide
└── README.md             # Master project documentation
```

---

## 🔑 Default Seed Credentials

Run `python scripts/seed_db.py` in the backend directory to seed default accounts:

| Role | Portal Login URL | Username / Email | Password | Scope |
|---|---|---|---|---|
| **ADMIN** | `http://localhost:5173/admin/login` | `admin@example.com` | `demo1234` | Full System Administration |
| **MENTOR** | `http://localhost:5173/mentor/login` | `605101` (or `mentor@example.com`) | `demo1234` | Assigned Students & Sections |
| **CR** | `http://localhost:5173/auth/login` | `cr@example.com` | `demo1234` | Section `II-A` (`2nd Year`) |
| **LR** | `http://localhost:5173/auth/login` | `lr@example.com` | `demo1234` | Section `II-A` (`2nd Year`) |

---

## ⚙️ Environment Setup

### 1. Backend Environment (`backend/.env`)

Create `backend/.env` with the following variables:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=college_session_monitoring
JWT_SECRET_KEY=supersecretkey_change_in_production_1234567890
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FRONTEND_URL=http://localhost:5173
TIMEZONE=Asia/Kolkata
```

### 2. Frontend Environment (`frontend/.env`)

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 🚀 Quick Start Guide

### Step 1: Start the Backend Server

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Seed MongoDB Atlas database
python scripts/seed_db.py

# 5. Launch FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend API Base**: `http://localhost:8000/api`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

### Step 2: Start the Frontend Application

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

- **Frontend Application URL**: `http://localhost:5173`

---

## 🧪 Running Automated Tests

Run the full pytest suite (35 automated tests covering authentication, session engine, attendance corrections, timetable parsing, mentor mapping, and planned absences):

```powershell
cd backend
$env:PYTHONPATH="backend"
venv\Scripts\activate
pytest backend/tests
```

Build the production frontend:

```powershell
cd frontend
npm run build
```

---

## 📋 Comprehensive API Route Matrix

| Domain | Method | Endpoint | Description | Roles |
|---|---|---|---|---|
| **Auth** | `POST` | `/api/auth/login` | JWT login for Admin, CR/LR, and Mentor | Public |
| **Auth** | `GET` | `/api/auth/me` | Current authenticated user profile | Authenticated |
| **Mentor Mapping** | `GET` | `/api/admin/mentor-student-mapping/template` | Download Excel mapping template | `ADMIN` |
| **Mentor Mapping** | `POST` | `/api/admin/mentor-student-mapping/preview` | Upload and preview Excel mappings | `ADMIN` |
| **Mentor Mapping** | `POST` | `/api/admin/mentor-student-mapping/import` | Commit mappings to MongoDB | `ADMIN` |
| **Mentor Mapping** | `GET` | `/api/admin/mentor-student-mapping` | List all active mentor mappings | `ADMIN` |
| **Mentor Mapping** | `DELETE` | `/api/admin/mentor-student-mapping/{id}` | Delete mapping and unassign students | `ADMIN` |
| **Planned Absence**| `POST` | `/api/mentor/planned-absences` | Schedule student planned absence | `MENTOR`, `ADMIN` |
| **Planned Absence**| `GET` | `/api/mentor/planned-absences` | List planned absences (scoped) | `MENTOR`, `ADMIN` |
| **Planned Absence**| `PATCH`| `/api/mentor/planned-absences/{id}` | Update dates or reason | `MENTOR`, `ADMIN` |
| **Planned Absence**| `POST` | `/api/mentor/planned-absences/{id}/cancel` | Cancel planned absence | `MENTOR`, `ADMIN` |
| **Planned Absence**| `GET` | `/api/admin/planned-absences` | Admin overview of all planned leaves | `ADMIN` |
| **Mentor Portal** | `GET` | `/api/mentor/dashboard` | Mentor dashboard overview | `MENTOR`, `ADMIN` |
| **Mentor Portal** | `GET` | `/api/mentor/students` | Monitored students list | `MENTOR`, `ADMIN` |
| **Mentor Portal** | `GET` | `/api/mentor/absentees` | Monitored section absentees | `MENTOR`, `ADMIN` |
| **Mentor Portal** | `PATCH`| `/api/mentor/absentees/{id}/comment` | Save absence note | `MENTOR`, `ADMIN` |
| **CR/LR Attendance**| `POST`| `/api/student-attendance/submit` | Submit section daily attendance | `CR`, `LR`, `ADMIN` |
| **CR/LR Attendance**| `POST`| `/api/student-attendance/correct` | Correct absent student to Present | `CR`, `LR`, `ADMIN` |
| **Timetable** | `POST` | `/api/timetable/upload` | Upload multi-sheet class timetable | `ADMIN` |
| **Sessions** | `GET` | `/api/sessions/active` | Active continuous teaching sessions | `CR`, `LR`, `ADMIN` |
| **Attendance** | `POST` | `/api/attendance/submit` | Hourly faculty presence response | `CR`, `LR`, `ADMIN` |
