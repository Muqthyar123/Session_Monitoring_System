# College Faculty Attendance & Session Monitoring System — Frontend

Frontend-only implementation. All data comes from a mock service layer; no backend
is connected. The backend (Python + FastAPI + MongoDB) will be implemented separately.

## Demo credentials (mock only — not real authentication)

| Role  | Email             | Password   |
| ----- | ----------------- | ---------- |
| ADMIN | admin@example.com | demo1234   |
| CR    | cr@example.com    | demo1234   |
| LR    | lr@example.com    | demo1234   |

## Routes

```
/                      Portal selection
/admin/login           Admin Login
/admin/dashboard       Admin Dashboard (analytics + recent alerts)
/admin/timetable       Timetable Management (upload, template, timetable view)
/admin/cr-lr           CR/LR Management (manual CRUD + Excel upload)
/admin/sessions        Sessions / Monitoring
/admin/alerts          Notifications / Alerts

/auth/login            CR / LR Login
/crlr/dashboard        CR/LR Dashboard (assigned section only)
/crlr/attendance       Faculty Attendance response + substitute reporting
/crlr/analytics        Section analytics
/crlr/notifications    Notification panel (read/unread)
```

Role-based access is enforced in the frontend by `src/components/common/RoleGuard.tsx`.
The backend must enforce the same rules.

## Project structure

```
src/
├── components/common/        StatCard, StatusBadge, DataTable, FileUpload, states, guard
├── components/sessions/      AttendanceForm, ResponseWindow
├── components/notifications/ NotificationBell
├── layouts/                  AdminLayout, CRLRLayout
├── routes/                   File-based routes (TanStack Router)
├── services/                 API abstraction (mock implementations today)
├── context/AuthContext.tsx   Demo session state
├── hooks/useAsyncData.ts     loading / error / retry helper
└── data/mock/mockData.ts     All mock data (delete when APIs are connected)
```

## Connecting the backend later

Replace the bodies of the functions in `src/services/*` with real HTTP calls using
`request()` from `src/services/apiClient.ts`. Component code does not need to change.

Backend responsibilities (not implemented in the frontend):
authentication/JWT, Excel parsing, session generation, continuous-period grouping,
the 10-minute response window timer, alert generation and notification delivery.

## Notes

- This project uses TanStack Router (file-based) rather than React Router DOM;
  the build stack does not support React Router DOM.
- Template downloads are generated client-side as CSV files with the required columns.
