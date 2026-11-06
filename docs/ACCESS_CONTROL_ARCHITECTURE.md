# Session Monitoring access architecture

## Current architecture (inspected 2026-11-06)

- Backend: asynchronous FastAPI, MongoDB through Motor, Pydantic request/response schemas, JWT bearer authentication. `get_current_user` reloads the account on each request, so role and active status are database-backed.
- Collections: `users`, `sites`, `branches`, `departments`, `students`, `sections`, `timetables`, `sessions`, `attendance_records`, `student_attendance`, `student_attendance_submissions`, `mentor_student_mappings`, `planned_absences`, notifications, and audit logs. Academic-year values currently live as labels on users/students/sections/timetables rather than a normalized collection.
- Existing management: `/api/super-admin` serves sites, branches and HOD account CRUD; `/api/admin/departments` serves departments; admin, mentor and CR/LR route groups serve operational workflows.
- Frontend: TanStack file routes, role layouts, typed API services. Super Admin has dashboard, sites, branches and HOD pages; departments currently have the admin department page. Auth state is loaded from `/api/auth/me`.
- Legacy identity fields use branch/department codes and section strings. Some service queries already scope mentor students through mapping records; other routes use branch-only filters or accept requested filters directly.

## Data and permission changes

Keep MongoDB and existing collections. A department remains a distinct document and must reference a branch (`branch_id` plus code/name denormalization for legacy readers). HOD accounts remain user documents with role `ADMIN`, with explicit `branch_id`, `department_id`, codes, and an `academic_years` array. Multiple user documents may reference the same department and year. Mentors keep explicit `academic_years` and branch/department assignments, while `mentor_student_mappings` remains the authority for student-level access. Existing labels in the four legacy years continue to work; configurable year catalogs are stored per department in its `academic_years` array.

The backend derives role and assignments from the reloaded database user. Scope checks intersect caller filters with those assignments; request values can narrow access but never widen it. CR/LR section checks and mentor student mappings remain the narrower rules for those roles. Super Admin access is unrestricted.

## Migration and compatibility

Startup migration is idempotent and preserves records. It creates only a neutral default site; it no longer invents branch/department assignments or provisions a known-password Super Admin. Operational records retain their existing IDs and year history. New department assignment fields are additive, and legacy code fields remain readable during transition. Do not run a destructive reset. Existing departments without a branch reference can be linked during a deliberate data migration once their owning branch is confirmed; do not guess this association for production records. Provision the first Super Admin explicitly with `python scripts/seed_db.py create-superadmin --email ... --name ...`.

## Implemented in this change

- Allow multiple HOD accounts per department, persist each HOD's department and year assignments, and validate years against that department's configured years.
- Stop branch creation from manufacturing a duplicate department; department creation is explicit and records the parent branch.
- Constrain HOD student, session, timetable, section, CR/LR, attendance, report, planned absence, and mentor-mapping operations by assigned department and academic years, including rejection of direct requests for an unassigned year.
- Preserve compatibility with existing branch and department code filters.
- Require Super Admin for bulk imports and destructive roster/timetable resets that do not yet support row-level HOD scoping. The explicitly provisioned first legacy Admin retains compatibility access until assigned an organization scope; newly scoped HOD accounts cannot use global imports.

## Follow-up coverage

The application still has independent workflow paths that need full integration and regression coverage, especially notification targeting, background-generated records, and migration of legacy documents whose branch/department ownership is ambiguous. Global bulk imports and resets are restricted to Super Admin and the explicitly provisioned, still-unscoped legacy Admin while parsers lack row-level HOD enforcement. The current schema does not yet have standalone `academic_years` documents; year labels are configured per department. These remaining cases need authorization tests against a seeded multi-branch MongoDB fixture before production rollout.
