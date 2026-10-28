# MongoDB Atlas integration audit

This document maps the persistent features present in the repository to their frontend entry points, API routes, and MongoDB collections. The configured repository-root `.env` is used locally; process environment variables override it for Render. The application uses `MONGODB_URI` and `DATABASE_NAME` only. See the environment templates for placeholders; never commit actual `.env` files.

## Runtime and persistence model

- `backend/app/db/mongodb.py` manages one async Motor client over FastAPI's lifespan, pings Atlas during startup, selects `DATABASE_NAME`, and closes the client on shutdown. Connection failures stop startup; there is no local, JSON, or in-memory runtime fallback.
- `backend/app/db/indexes.py` creates indexes against that database and will not silently ignore index failures. It checks for duplicates before replacing incompatible legacy indexes.
- Backend route handlers and services use the shared database manager. The test suite substitutes an in-memory database only in test fixtures.
- Frontend domain records load and mutate through the typed service modules and FastAPI. The former mock-data module now contains types only. Browser `localStorage` holds the JWT only; the profile is loaded from `/api/auth/me` after reload. `sessionStorage` is limited to temporary filter selections.
- Excel templates are generated in memory; imports write parsed rows to the appropriate MongoDB collections. The original file is not retained, but import summaries (filename and saved/rejected counters) are persisted in `audit_logs` and exposed through the admin upload-history API.
- Uploads are bounded to `MAX_UPLOAD_SIZE_MB` (default 20 MB) and `MAX_IMPORT_ROWS` (default 10,000 rows). The browser reports actual file-transfer progress, then an indeterminate “validating and saving” phase; the API responds only after synchronous parsing and database writes finish.
- No startup or scheduled task clears permanent roster, timetable, attendance, mapping, or upload-audit collections. Timetable reconciliation now deactivates stale sections instead of deleting them; duplicate section documents are merged before duplicate records are removed.

## Feature-to-database map

| Feature | Frontend pages/services | API routes | MongoDB collections |
|---|---|---|---|
| Authentication, accounts, CR/LR, mentors | `admin.login`, `auth.login`, `mentor.login`; `authService`, `userService`, `mentorService` | `/api/auth/*`, `/api/admin/users/*`, `/api/admin/mentors/*` | `users`, `audit_logs` |
| Students and roster imports | `admin.students`; `studentService` | `/api/admin/students/*` | `students`, `sections`, `users` (representative assignment), `audit_logs` |
| Sections and assignments | `admin.sections`; `sectionService` | `/api/sections/*` | `sections`, `students`, `users`, `timetables` |
| Departments and coordinators | `admin.departments`; `departmentService` | `/api/admin/departments/*` | `departments`, `students`, `sections`, `users` |
| Timetable and Excel upload | `admin.timetable`; `timetableService` | `/api/admin/timetable/*` | `timetables`, `sections`, `users` (faculty accounts), `audit_logs` |
| Session generation and monitoring | `admin.sessions`, `crlr.attendance`; `sessionService` | `/api/sessions/*`, `/api/attendance/*` | `sessions`, `attendance_records`, `admin_alerts`, `audit_logs`, `notifications` |
| Student attendance, corrections, history | `crlr.student-attendance`, `admin.student-history`, `admin.student-analytics`; `studentAttendanceService` | `/api/crlr/*`, `/api/student-attendance/*`, `/api/analytics/student-*` | `student_attendance`, `student_attendance_submissions`, `students`, `users`, `audit_logs` |
| Mentor dashboard, monitored students, absentee notes | `mentor.dashboard`, `mentor.students`, `mentor.absentees`, `mentor.analytics`; `mentorService` | `/api/mentor/*`, `/api/mentor/absentees/*`, `/api/analytics/faculty/*` | `users`, `students`, `student_attendance`, `sessions`, `attendance_records` |
| Mentor-student assignments | `admin.mentor-mapping`; `mentorMappingService` | `/api/admin/mentor-student-mapping/*` | `mentor_student_mappings`, `students`, `users`, `audit_logs` |
| Upload history | Admin dashboard; `uploadService` | `/api/admin/uploads/history` | `audit_logs` |
| Planned absences | `mentor.planned-absences`; `plannedAbsenceService` | `/api/mentor/planned-absences/*`, `/api/admin/planned-absences` | `planned_absences`, `students`, `users`, `audit_logs` |
| Alerts and notifications | `admin.alerts`, `crlr.notifications`, notification bell; `notificationService` | `/api/attendance/alerts/*`, `/api/notifications/*` | `admin_alerts`, `notifications` |
| Browser push subscriptions | notification components; push API client | `/api/push/register` | `push_subscriptions` |
| Dashboards and reports | `admin.dashboard`, `admin.analytics`, `crlr.analytics`, `mentor.analytics`; analytics services | `/api/analytics/*` | Aggregations over `users`, `students`, `sections`, `sessions`, `attendance_records`, `student_attendance`, `student_attendance_submissions`, and `admin_alerts` |

Collections actually referenced by the application are `users`, `students`, `sections`, `departments`, `timetables`, `sessions`, `attendance_records`, `admin_alerts`, `student_attendance`, `student_attendance_submissions`, `notifications`, `push_subscriptions`, `planned_absences`, `mentor_student_mappings`, and `audit_logs`.

## Upload-to-collection workflow

| Upload workflow | Persisted records and related writes |
|---|---|
| CR/LR roster (`.xlsx`, `.xls`, `.csv`) | `users` for CR/LR accounts, section assignment fields in `sections`, import counters in `audit_logs` |
| Mentor roster (`.xlsx`, `.xls`, `.csv`) | `users` with mentor/employee identity, import counters in `audit_logs` |
| Student roster (`.xlsx`, `.xls`, `.csv`) | `students`, optional representative references, import counters in `audit_logs` |
| Timetable (`.xlsx`, `.xls`) | `timetables` periods, `sections`, discovered faculty entries in `users`, import counters in `audit_logs`; session records are generated by the existing scheduler |
| Mentor mapping (`.xlsx`, `.xls`) | Preview validates first; confirmed rows update `mentor_student_mappings` and related `students`, with counters in `audit_logs` |

All file uploads are limited by `MAX_UPLOAD_SIZE_MB` (20 MB default) and `MAX_IMPORT_ROWS` (10,000 default). Supported import endpoints validate the extension and contents and return row-level validation failures without falsely claiming a full import. A fully rejected but parseable roster/timetable returns a failure summary with its row errors so the frontend can show the rejected rows. The frontend's transfer percentage comes from browser upload events; after transfer it displays an indeterminate backend-validation/database-save stage until the endpoint returns.

## API operation inventory

All paths are prefixed with `/api`; protected routes enforce the role dependencies in the backend.

| API route group | Supported operations |
|---|---|
| `/auth` | `POST /login`, `GET /me`, `POST /change-password` |
| `/admin/users` | `GET`, `POST`, `GET /{user_id}`, `PATCH /{user_id}`, `DELETE /{user_id}`, `DELETE /reset`, `GET /template`, `POST /import` |
| `/admin/mentors` | `GET`, `POST`, `PATCH /{mentor_id}`, `DELETE /{mentor_id}`, `DELETE /reset`, `GET /template`, `POST /import` |
| `/admin/students` | `GET` (filter/search/page), `GET /filters`, `POST`, `PATCH /{student_id}`, `DELETE /{student_id}`, `DELETE /reset`, `GET /template`, `POST /import` |
| `/sections` | `GET`, `POST`, `PUT /{section_id}`, `DELETE /{section_id}` |
| `/admin/departments` | `GET`, `POST`, `PUT /{dept_id}`, `DELETE /{dept_id}` |
| `/admin/timetable` | `GET`, `GET /{section}`, `POST /upload`, `GET /template`, `DELETE`, `DELETE /{section}`, `POST /reset`; full deletion reports timetable, generated-session, and attendance record counts and writes an audit entry |
| `/admin/uploads` | `GET /history` (paginated, administrator-only persisted import summaries) |
| `/sessions` | `GET`, `GET /today`, `GET /active`, `GET /{session_id}` |
| `/attendance` | `POST`, `GET /my`, `GET /alerts`, `PATCH /alerts/{alert_id}/acknowledge` |
| Student attendance | `GET /crlr/students`, `GET /crlr/student-attendance/status`, `POST /crlr/student-attendance`, `POST|PATCH /crlr/student-attendance/correct`, `PATCH /crlr/student-attendance/{record_id}/correct`, `PATCH /student-attendance/{record_id}/correct`, mentor absentee year/section/list/reason routes, and student summary/history analytics routes |
| `/mentor` | Dashboard, monitored student years/sections/lists/search, absentee years/sections/lists/search, and `PATCH /absentees/{record_id}/comment` or `PUT /absentees/{record_id}/reason` |
| `/admin/mentor-student-mapping` | `GET`, `GET /template`, `POST /preview`, `POST /import`, `DELETE /{mapping_id}` |
| Planned absences | Mentor create/list/update/cancel; administrator list at `/admin/planned-absences` |
| `/notifications` | `GET`, `GET /unread-count`, `PATCH /{notification_id}/read`, `PATCH /read-all` |
| `/push/register` | `POST` register, `DELETE` unregister |
| Analytics | `/admin/analytics`, `/crlr/analytics`, `/analytics/faculty`, and faculty history routes under `/analytics/faculty/{faculty_name}/history` and `/admin/faculty/{faculty_name}/history` |

## Local and production run settings

Local backend (after setting the repository-root `.env` and creating a virtual environment):

```powershell
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_db.py create --email moturisireesha@gmail.com --name Sireesha
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Local frontend: set `VITE_API_BASE_URL=http://localhost:8000/api` in `frontend/.env`, then run `npm install` and `npm run dev`. In production, configure the frontend provider's build environment with the deployed backend URL ending in `/api`; the browser client refuses a missing or localhost production URL. Configure Render's `MONGODB_URI`, `FRONTEND_URL`, and generated `JWT_SECRET_KEY` through the Blueprint/service settings. The Atlas database user needs read/write permissions for `college_session_monitoring_system` and Atlas network access must allow the backend.

Create the intended first administrator using `python scripts/seed_db.py create --email moturisireesha@gmail.com --name Sireesha` from `backend`. It prompts securely for an 8–12 character password and hashes it. `verify --email moturisireesha@gmail.com` checks an existing account; `reset-password --email moturisireesha@gmail.com` changes only the password of an existing ADMIN account. No password is accepted on the command line or stored in source.

## Verification and limits

- Backend suite: `68 passed, 1 skipped` using the isolated in-memory test fixture. The skipped test is the separate Atlas test when no test database is set in the normal suite run.
- Frontend production build: succeeded.
- Supported file uploads: CR/LR, mentor, and student roster imports accept `.xlsx`, `.xls`, and `.csv`; timetable imports accept `.xlsx` and `.xls`; mentor mapping preview accepts `.xlsx` and `.xls`. No JSON upload is implemented or claimed.
- Uploads are synchronous, bounded operations. Transfer percentage is real browser transfer progress; server-side validation and MongoDB persistence display as an indeterminate phase and success is shown only after the API returns. There is no resumable background-job ID or per-row live polling endpoint.
- MongoDB Atlas: configured host ping succeeded. A read-only lookup found no account for `moturisireesha@gmail.com` and zero administrators in `college_session_monitoring_system`; no account or application data was changed during that check.
- Real Atlas verification: the extended opt-in integration test passed against the isolated database `fams_test_persist_20261028`. It provisioned a test admin, authenticated through `/api/auth/login`, accessed a protected endpoint, created and updated a student, imported a workbook, verified its MongoDB record and API retrieval, retried the import without creating a duplicate, closed/reopened the Mongo client, confirmed both student records persisted, and cleaned up its generated rows and audit records. This did not modify the configured application database.
- Atlas identified the connected database user as `atlasAdmin` on the `admin` database. That role has enough access for the verified CRUD and index operations, but it is broader than the application needs; use a least-privilege `readWrite` role scoped to `college_session_monitoring_system` for deployment when practical.
- Persistence after a real backend process restart, browser refresh, and live CRUD in `college_session_monitoring_system` have not been verified in this implementation turn. The integration test verifies persistence after closing and reopening the Mongo client, which is not the same as restarting the process. Keep test operations in a separate database; the opt-in test refuses to run if its name equals `DATABASE_NAME`.
- Standalone frontend lint and TypeScript checks did not complete in this Windows workspace: both commands remained running without diagnostics and had to be interrupted. The production bundler succeeded, but it is not a replacement for these checks.
- To verify persistent records manually, open Atlas **Browse Collections** and select `college_session_monitoring_system`, then inspect the collections in the map above. Verify the first admin after running the seed script in `users` (role `ADMIN`); do not inspect or export password hashes.

To repeat the real integration test safely, choose an isolated Atlas test database name distinct from `DATABASE_NAME` and shorter than Atlas's database-name limit, then run from `backend`:

```powershell
$env:MONGODB_TEST_DATABASE_NAME = "fams_test_your_suffix"
pytest -q tests/test_atlas_integration.py
```
