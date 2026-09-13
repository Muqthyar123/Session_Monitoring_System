# College Faculty Attendance & Session Monitoring System - Backend

Production-structured, asynchronous **FastAPI + MongoDB** backend for the **College Faculty Attendance & Session Monitoring System**.

Designed to interface seamlessly with a React frontend, this backend provides role-based authorization (ADMIN, CR, LR), dynamic timetable period parsing with continuous session detection, automated session start notifications, immediate faculty absence alerts, 10-minute non-response escalation alerts, Excel template generation/imports, and real-time MongoDB analytics.

---

## 🌟 Key Features

1. **Role-Based Authorization (JWT + Bcrypt)**
   - Roles: `ADMIN`, `CR` (Class Representative), `LR` (Lady Representative).
   - Secure password hashing using `bcrypt`.
   - Strict API route protection: CR/LR users are restricted exclusively to their assigned section.

2. **Continuous Session Engine**
   - Automatically parses timetable periods for each section.
   - Combines consecutive periods of the same subject and faculty into **one continuous session** (e.g. Period 1: 09:10–10:00 DBMS, Period 2: 10:00–10:50 DBMS, Period 3: 10:50–11:40 DBMS -> **ONE session: 09:10–11:40**).
   - Sends only **ONE** notification at the start of a continuous session block.

3. **APScheduler Background Jobs & Escalation Engine**
   - Operates centrally in `Asia/Kolkata` (`UTC+05:30`) timezone.
   - Idempotent execution prevents duplicate notifications or alerts upon server restarts.
   - **Immediate Absence Alert**: Instant admin notification when CR/LR reports faculty `ABSENT` or `SUBSTITUTE`.
   - **10-Minute Escalation Alert**: Automatically alerts Admin if CR/LR fails to respond within 10 minutes of session start time.

4. **Excel Processing (`openpyxl` + `pandas`)**
   - Dynamic template generation for CR/LR user list and Class Timetables (`.xlsx`).
   - Safe Excel import parsers with detailed row-by-row error reporting (`total_rows`, `created`, `updated`, `failed`, `errors`).

5. **In-App & Browser Push Notifications (FCM Integration Structure)**
   - Firebase Cloud Messaging integration for browser push notifications.
   - In-app notification center stored in MongoDB (`notifications` collection).

6. **Real-time Analytics**
   - Real-time aggregation pipelines for Admin and CR/LR dashboards (presence percentages, section-wise stats, response rates).

---

## 📁 Repository Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI Application Entrypoint & Middleware
│   ├── api/                    # REST API Endpoints
│   │   ├── auth.py             # Login, Current User, Password Change
│   │   ├── users.py            # User CRUD & CR/LR Excel Import/Template
│   │   ├── sections.py         # Section Management
│   │   ├── timetable.py        # Timetable Upload, Viewing, Template Download
│   │   ├── sessions.py         # Daily, Active, and Section Sessions
│   │   ├── attendance.py       # Attendance Submission & Admin Alerts
│   │   ├── notifications.py    # In-App Notifications API
│   │   ├── push.py             # Browser Push Registration API
│   │   └── analytics.py        # Admin & CR/LR Dashboard Analytics
│   ├── core/
│   │   ├── config.py           # Application Settings (Pydantic BaseSettings)
│   │   ├── security.py         # Bcrypt Password Hashing & JWT Processing
│   │   └── dependencies.py     # Auth Dependencies & RBAC Checks
│   ├── db/
│   │   ├── mongodb.py          # Async Motor Database Client
│   │   └── indexes.py          # MongoDB Database Index Initialization
│   ├── models/                 # Database Document Specifications
│   ├── schemas/                # Pydantic v2 Input/Output DTOs & Validation
│   ├── services/               # Core Business Logic & Algorithms
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── timetable_service.py
│   │   ├── session_service.py  # Continuous Session Merger Algorithm
│   │   ├── attendance_service.py
│   │   ├── notification_service.py
│   │   ├── push_service.py     # FCM Integration Service
│   │   ├── analytics_service.py
│   │   └── excel_service.py    # Excel Template Generator & Parsers
│   └── scheduler/
│       ├── scheduler.py        # APScheduler AsyncIOScheduler Setup
│       └── jobs.py             # Scheduled Notification & Escalation Jobs
├── scripts/
│   └── seed_db.py              # Development Database Seed Script
├── tests/                      # Automated Test Suite (pytest)
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_sessions.py
│   ├── test_attendance.py
│   └── test_escalation.py
├── .env.example                # Sample Environment Variables
├── pytest.ini                  # Pytest Configuration
├── requirements.txt            # Python Dependencies
└── README.md                   # Backend Documentation
```

---

## 🛠️ Setup Instructions

### Prerequisites
- **Python 3.11+** installed
- **MongoDB** running locally (`mongodb://localhost:27017`) or a MongoDB Atlas URI

### 1. Create Virtual Environment & Install Dependencies

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and set your configuration options:

```bash
cp .env.example .env
```

`.env` configuration keys:
```env
MONGODB_URI=mongodb://localhost:27017
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

### 3. Seed Development Data

Run the database seed script to populate default Admin, CR, LR accounts, sections, and sample timetables:

```bash
python scripts/seed_db.py
```

Default Seed Credentials:
- **Admin**: `admin@example.com` / `demo1234`
- **CR (II-A)**: `cr@example.com` / `demo1234`
- **LR (II-A)**: `lr@example.com` / `demo1234`

---

## 🚀 Running the Server

Start the FastAPI backend with Uvicorn live reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- ReDoc API Documentation: `http://localhost:8000/redoc`

---

## 🧪 Running Automated Tests

Run the backend test suite using `pytest` (uses in-memory `mongomock_motor` for zero-side-effect, high-speed execution):

```bash
pytest
```

---

## 📄 Key API Contracts

### Authentication
- `POST /api/auth/login`: Authenticates user and returns JWT bearer token + role details.
- `GET /api/auth/me`: Returns profile info of authenticated user.
- `POST /api/auth/change-password`: Updates password.

### Admin User & Section Management
- `GET /api/admin/users`: List users with filtering (`role`, `section`, `year`, `search`).
- `POST /api/admin/users`: Create user account.
- `PATCH /api/admin/users/{user_id}`: Update user account.
- `DELETE /api/admin/users/{user_id}`: Delete user account.
- `GET /api/admin/users/template`: Download CR/LR Excel template (`.xlsx`).
- `POST /api/admin/users/import`: Upload CR/LR Excel workbook.
- `GET /api/sections`: List active sections and assigned CR/LR names.

### Timetable
- `GET /api/admin/timetable/template`: Download official Timetable Excel template (`.xlsx`).
- `POST /api/admin/timetable/upload`: Upload class timetable Excel workbook.
- `GET /api/admin/timetable/{section}`: View timetable for a specific section.

### Class Sessions & Attendance
- `GET /api/sessions/today`: List today's active/upcoming sessions.
- `GET /api/sessions/active`: List currently active sessions.
- `POST /api/attendance`: Submit attendance (`PRESENT`, `ABSENT`, `SUBSTITUTE`).
- `GET /api/attendance/alerts`: View active Admin Alerts.

### Analytics & Push Notifications
- `GET /api/admin/analytics`: Real-time system analytics for Admin Dashboard.
- `GET /api/crlr/analytics`: Section-specific analytics for CR/LR Dashboard.
- `POST /api/push/register`: Register device push notification token.

---

## 🔒 Deployment & Production Notes

1. Set `JWT_SECRET_KEY` to a cryptographically strong random secret.
2. Provide valid Firebase service account credentials (`FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL`) to enable live FCM push notifications.
3. Configure `FRONTEND_URL` to match your deployed React app URL for CORS enforcement.
4. Run behind a production ASGI server like Uvicorn with multiple workers or Gunicorn (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`).
