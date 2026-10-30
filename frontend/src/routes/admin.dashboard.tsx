import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Layers,
  UserCheck,
  UserX,
  Users,
  CalendarClock,
  Clock,
  Repeat2,
  UserCog,
} from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ChartCard } from "@/components/common/ChartCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { DataTable, type Column } from "@/components/common/DataTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getAdminDashboard, getAlerts } from "@/services/sessionService";
import type { AdminAlert } from "@/data/mock/mockData";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getUploadHistory } from "@/services/uploadService";
import { useAuth } from "@/context/AuthContext";
import { getAdminStudentAttendanceSummary } from "@/services/studentAttendanceService";

export const Route = createFileRoute("/admin/dashboard")({
  head: () => ({
    meta: [
      { title: "Admin Dashboard — Faculty Attendance Monitor" },
      { name: "description", content: "Daily faculty presence, section-wise monitoring, session status and recent attendance alerts." },
      { property: "og:title", content: "Admin Dashboard — Faculty Attendance Monitor" },
      { property: "og:description", content: "Daily faculty presence and session monitoring overview." },
    ],
  }),
  component: AdminDashboardPage,
});

const PIE_COLORS = [
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-1)",
];

const alertColumns: Column<AdminAlert>[] = [
  { key: "section", header: "Section", cell: (r) => r.section },
  { key: "subject", header: "Subject", cell: (r) => r.subject },
  { key: "session", header: "Session", cell: (r) => r.session },
  { key: "reportedBy", header: "Reported by", cell: (r) => r.reportedBy },
  { key: "reason", header: "Reason", cell: (r) => r.reason },
  { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
];

function AdminDashboardPage() {
  const { user } = useAuth();
  const dashboard = useAsyncData(() => getAdminDashboard(), [], 15000);
  const alerts = useAsyncData(() => getAlerts(), [], 15000);
  const uploads = useAsyncData(
    () => user?.role === "ADMIN" ? getUploadHistory(0, 8) : Promise.resolve([]),
    [user?.role],
    15000,
  );
  const studentAttendance = useAsyncData(() => getAdminStudentAttendanceSummary(), [], 15000);

  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <AdminLayout>
      <PageHeader title="Dashboard" description={today} />

      <Card>
        <CardHeader><CardTitle>Student Attendance by Session</CardTitle><CardDescription>Attendance submissions saved in MongoDB. Refreshes every 15 seconds.</CardDescription></CardHeader>
        <CardContent>
          {studentAttendance.loading ? <LoadingState rows={2} label="Loading student attendance..." /> : studentAttendance.error ? <ErrorState message={studentAttendance.error} onRetry={studentAttendance.reload} /> : <div className="space-y-3">
            <div className="flex flex-wrap gap-4 text-sm font-medium"><span>Present: {studentAttendance.data?.totalPresent ?? 0}</span><span>Absent: {studentAttendance.data?.totalAbsent ?? 0}</span><span>Completed: {studentAttendance.data?.completedSubmissions ?? 0}</span></div>
            {studentAttendance.data?.sessions.length ? <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">Year</th><th className="p-2">Branch · Section</th><th className="p-2">Session</th><th className="p-2">Present / Absent</th><th className="p-2">Rate</th><th className="p-2">Submission</th></tr></thead><tbody>{studentAttendance.data.sessions.map((item) => <tr key={`${item.year}-${item.section}-${item.sessionId}`} className="border-b"><td className="p-2">{item.year}</td><td className="p-2">{item.branch || "—"} · {item.section}</td><td className="p-2">{item.sessionId === "SESSION_1" ? "Before Lunch" : item.sessionId === "SESSION_2" ? "After Lunch" : item.sessionId}</td><td className="p-2">{item.present} / {item.absent}</td><td className="p-2">{item.attendancePercentage}%</td><td className="p-2">{item.status}{item.submittedBy ? ` · ${item.submittedBy}` : ""}</td></tr>)}</tbody></table></div> : <EmptyState title="No student attendance submitted" description="Today's session submissions will appear here." />}
          </div>}
        </CardContent>
      </Card>

      {dashboard.loading ? (
        <LoadingState rows={5} label="Loading dashboard..." />
      ) : dashboard.error ? (
        <ErrorState message={dashboard.error} onRetry={dashboard.reload} />
      ) : dashboard.data ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total Sections" value={dashboard.data.summary.totalSections} icon={Layers} />
            <StatCard label="Total CRs" value={dashboard.data.summary.totalCRs} icon={Users} />
            <StatCard label="Total LRs" value={dashboard.data.summary.totalLRs} icon={UserCog} />
            <StatCard label="Today's Sessions" value={dashboard.data.summary.todaysSessions} icon={CalendarClock} />
            <StatCard label="Faculty Present" value={dashboard.data.summary.facultyPresent} icon={UserCheck} tone="success" />
            <StatCard label="Faculty Absent" value={dashboard.data.summary.facultyAbsent} icon={UserX} tone="destructive" />
            <StatCard label="Pending Responses" value={dashboard.data.summary.pendingResponses} icon={Clock} tone="warning" />
            <StatCard label="Substitute Faculty" value={dashboard.data.summary.substituteFaculty} icon={Repeat2} tone="info" />
          </section>

          <Card>
            <CardContent className="space-y-2 p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Faculty Presence (today)</span>
                <span className="text-muted-foreground">{dashboard.data.facultyPresencePercent}%</span>
              </div>
              <Progress value={dashboard.data.facultyPresencePercent} />
            </CardContent>
          </Card>

          <section className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Section-wise Monitoring" description="Faculty presence by section (today)">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboard.data.sectionWise}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="section" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="present" name="Present" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="absent" name="Absent" fill="var(--color-chart-4)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="substitute" name="Substitute" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Session Status" description="Responses recorded for today's sessions">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dashboard.data.sessionStatus}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    isAnimationActive={false}
                  >
                    {dashboard.data.sessionStatus.map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </section>
        </>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Recent Alerts</h2>
        {alerts.loading ? (
          <LoadingState rows={3} />
        ) : alerts.error ? (
          <ErrorState message={alerts.error} onRetry={alerts.reload} />
        ) : (alerts.data?.length ?? 0) === 0 ? (
          <EmptyState title="No alerts" description="No faculty attendance alerts have been raised today." />
        ) : (
          <DataTable columns={alertColumns} rows={alerts.data ?? []} getRowId={(r) => r.id} />
        )}
      </section>

      {user?.role === "ADMIN" ? <Card>
        <CardHeader>
          <CardTitle>Recent Imports</CardTitle>
          <CardDescription>Saved upload summaries from MongoDB. Refreshes with the dashboard.</CardDescription>
        </CardHeader>
        <CardContent>
          {uploads.loading ? (
            <LoadingState rows={2} label="Loading import history..." />
          ) : uploads.error ? (
            <ErrorState message={uploads.error} onRetry={uploads.reload} />
          ) : (uploads.data?.length ?? 0) === 0 ? (
            <EmptyState title="No import history" description="Completed uploads will appear here." />
          ) : (
            <div className="space-y-3">
              {uploads.data?.map((item) => {
                const metadata = item.metadata || {};
                const imported = Number(metadata["created"] ?? metadata["inserted"] ?? 0);
                const updated = Number(metadata["updated"] ?? metadata["modified"] ?? 0);
                const failed = Number(metadata["failed"] ?? 0);
                const skipped = Number(metadata["unchanged"] ?? metadata["duplicate_rows"] ?? 0);
                const title = String(metadata["filename"] || item.action.replaceAll("_", " ").toLowerCase());
                return (
                  <div key={item.id} className="flex flex-col gap-1 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{title}</p>
                      <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                    <p className="shrink-0 text-xs text-muted-foreground">
                      {imported} created · {updated} updated · {skipped} skipped · {failed} failed
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card> : null}
    </AdminLayout>
  );
}
