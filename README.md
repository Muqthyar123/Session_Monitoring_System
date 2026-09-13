# College Faculty Attendance & Session Monitoring System

A production-ready, full-stack web application designed for colleges to automate faculty attendance tracking, session monitoring, substitute reporting, and administrative escalations using uploaded timetables.

Built with a **React + Tailwind CSS** frontend, a **Python FastAPI** REST API backend, and **MongoDB Atlas** cloud database storage.

---

## 🌟 System Highlights & Key Features

- **Role-Based Access Control (RBAC)**: Distinct portals and capabilities for **ADMIN**, **CR** (Class Representative), and **LR** (Lady Representative).
- **Continuous Session Engine**: Intelligently combines consecutive timetable periods of the same subject and faculty into **one single continuous teaching session** (e.g., Period 1: 09:10–10:00, Period 2: 10:00–10:50, Period 3: 10:50–11:40 DBMS → **ONE Session: 09:10–11:40**), preventing notification spam.
- **Automated Notifications**: Sends in-app and browser push notifications to section CR/LR users at class start time.
- **Immediate Absence Escalation**: Instantly generates an Admin Alert (`FACULTY_REPORTED_ABSENT`) when a CR or LR explicitly reports faculty as `ABSENT` or `SUBSTITUTE`.
- **10-Minute Timeout Escalation**: An automated background scheduler (`APScheduler`) checks for unanswered sessions and generates an Admin Alert (`NO_RESPONSE`) if no response is received within 10 minutes of class start.
- **Excel Workbook Processing**: Supports Excel (`.xlsx`) imports for CR/LR user enrollment and multi-sheet class timetables, with automated template downloads.
- **Real-Time Dynamic Analytics**: Real-time aggregation pipelines calculate live presence percentages, section-wise breakdowns, daily/weekly stats, and response rates.

---

## 🏗️ Technology Stack

### Frontend
- **Framework**: React 19 + TypeScript
- **Routing**: TanStack Router (File-based)
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Charts**: Recharts
- **Icons**: Lucide React
- **HTTP Client**: Centralized Fetch API Client with JWT Bearer Authentication

### Backend
- **Framework**: Python 3.13 / FastAPI
- **Database**: MongoDB Atlas (`motor` async driver)
- **Authentication**: JWT (`pyjwt`) with `bcrypt` password hashing
- **Scheduler**: `APScheduler` (AsyncIOScheduler) running in `Asia/Kolkata` (`UTC+05:30`) timezone
- **Excel Processing**: `openpyxl`, `pandas`
- **Push Notifications**: Firebase Cloud Messaging (FCM integration structure)
- **Testing**: `pytest`, `pytest-asyncio`, `httpx`, `mongomock-motor`

---

## 📂 Repository Directory Structure

```text
Session_Monitoring_System/
├── backend/
│   ├── app/
│   │   ├── api/          # REST API Endpoints (auth, users, sections, timetable, sessions, attendance, notifications, push, analytics)
│   │   ├── core/         # Settings configuration, JWT security & RBAC dependencies
│   │   ├── db/           # Async MongoDB Motor connection manager & index setup
│   │   ├── models/       # Database document specifications
│   │   ├── schemas/      # Pydantic v2 validation DTOs
│   │   ├── services/     # Business logic, Excel parsers, notification service & continuous session merger algorithm
│   │   └── scheduler/    # APScheduler background escalation jobs
│   ├── scripts/          # Database seeding script (seed_db.py)
│   ├── tests/            # Automated test suite (pytest)
│   ├── .env.example      # Backend environment settings template
│   ├── pytest.ini        # Pytest configuration
│   ├── requirements.txt  # Python package dependencies
│   └── README.md         # Backend technical documentation
├── frontend/
│   ├── src/
│   │   ├── components/   # UI components, tables, attendance form, notification bell
│   │   ├── layouts/      # Admin & CR/LR layout wrappers
│   │   ├── routes/       # TanStack file-based routes
│   │   ├── services/     # API service layer connected to FastAPI backend
│   │   └── data/mock/    # TypeScript interface DTOs
│   ├── .env.example      # Frontend environment settings template
│   ├── package.json      # Frontend npm dependencies
│   ├── vite.config.ts    # Vite configuration
│   └── README.md         # Frontend technical documentation
└── README.md             # Master project documentation
```

---

## 🔑 Default Seed Credentials

Run `python scripts/seed_db.py` in the backend to insert these initial accounts into your MongoDB Atlas database:

| Role | Portal URL | Email | Password | Assigned Section |
| --- | --- | --- | --- | --- |
| **ADMIN** | `http://localhost:5173/admin/login` | `admin@example.com` | `demo1234` | System-wide Admin |
| **CR** | `http://localhost:5173/auth/login` | `cr@example.com` | `demo1234` | `II-A` (`2nd Year`) |
| **LR** | `http://localhost:5173/auth/login` | `lr@example.com` | `demo1234` | `II-A` (`2nd Year`) |

---

## ⚙️ Environment Setup

### 1. Backend Environment (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and update your MongoDB Atlas connection URI:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=college_session_monitoring
JWT_SECRET_KEY=supersecretkey_change_in_production_1234567890
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FRONTEND_URL=http://localhost:5173
TIMEZONE=Asia/Kolkata
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=
```

### 2. Frontend Environment (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 🚀 Quick Start Guide

### Step 1: Start the Backend Server & Seed Database

Open Terminal 1 (PowerShell / Terminal):

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# 3. Seed MongoDB Atlas database with default accounts & sample data
python scripts/seed_db.py

# 4. Launch FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend API Base**: `http://localhost:8000/api`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`

### Step 2: Start the Frontend Application

Open Terminal 2 (PowerShell / Terminal):

```powershell
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Launch Vite dev server
npm run dev
```

- **Frontend Application URL**: `http://localhost:5173`

---

## 🧪 Running Automated Tests

Run the backend test suite using `pytest` (uses in-memory `mongomock_motor` for zero-side-effect, high-speed test execution):

```powershell
cd backend
venv\Scripts\activate
pytest
```

---

## 📌 Main Workflow Summary

1. **ADMIN**:
   - Logs in -> Views dynamic dashboard analytics & recent attendance alerts.
   - Uploads class timetables (`.xlsx`) or CR/LR student lists.
   - Downloads standard formatted Excel templates.

2. **SESSION ENGINE**:
   - Reads timetable data -> Merges consecutive periods into continuous class sessions.
   - Sends **ONE** notification to CR/LR at session start time.

3. **CR / LR**:
   - Logs in -> Views assigned section's active & upcoming sessions.
   - Receives start notification -> Submits attendance response:
     - **PRESENT**: Faculty is present.
     - **ABSENT**: Faculty is absent -> **Immediately alerts Admin**.
     - **SUBSTITUTE**: Substitute faculty present -> Enter substitute name -> **Alerts Admin**.

4. **10-MINUTE ESCALATION**:
   - If no response is submitted by CR/LR within 10 minutes of session start time, the backend `APScheduler` automatically generates a `NO_RESPONSE` Admin Alert.
