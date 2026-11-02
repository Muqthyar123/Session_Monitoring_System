import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
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
  Plus,
  Trash2,
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { cancelAttendanceSuspension, createAttendanceSuspension, getAttendanceSuspensions, type AttendanceSuspension } from "@/services/studentAttendanceService";
import { getStudentFilterOptions } from "@/services/studentService";
import { getSections, type Section } from "@/services/sectionService";

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
  const alerts = useAsyncData(() => {
    const day = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
    return getAlerts(undefined, undefined, { fromDate: day, toDate: day });
  }, [], 15000);
  const uploads = useAsyncData(
    () => user?.role === "ADMIN" ? getUploadHistory(0, 8) : Promise.resolve([]),
    [user?.role],
    15000,
  );
  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <AdminLayout>
      <PageHeader title="Dashboard" description={today} />
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

      {user?.role === "ADMIN" && <AttendanceSuspensionPanel />}

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

function AttendanceSuspensionPanel() {
  const suspensions = useAsyncData<AttendanceSuspension[]>(getAttendanceSuspensions, [], 15000);
  const yearsData = useAsyncData(getStudentFilterOptions, []);
  const [scopes, setScopes] = useState<Array<{ id: number; year: string; section: string }>>([{ id: 0, year: "", section: "" }]);
  const [nextScopeId, setNextScopeId] = useState(1);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [type, setType] = useState("BOTH");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const activate = async () => {
    const sectionsByYear: Record<string, string[]> = {};
    const allSectionsYears: string[] = [];
    for (const scope of scopes) {
      const year = scope.year.trim();
      if (!year) { toast.error("Select an academic year for every scope row."); return; }
      if (scope.section === "__ALL_SECTIONS__") allSectionsYears.push(year);
      else if (!scope.section) { toast.error(`Select a section or All Sections for ${year}.`); return; }
      else sectionsByYear[year] = [...(sectionsByYear[year] || []), scope.section];
    }
    const allYears = new Set(allSectionsYears);
    for (const year of allYears) delete sectionsByYear[year];
    const years = [...new Set([...Object.keys(sectionsByYear), ...allSectionsYears])];
    if (!years.length || !startDate || !endDate) { toast.error("Choose at least one year and both dates."); return; }
    const confirmed = window.confirm(`Suspend ${type.toLowerCase()} attendance for ${years.join(", ")} from ${startDate} through ${endDate}?`);
    if (!confirmed) return;
    setSaving(true);
    setRetrying(false);
    try {
      await createAttendanceSuspension({ years, sectionsByYear, allSectionsYears, startDate, endDate, attendanceType: type, reason }, () => setRetrying(true));
      toast.success("Attendance suspension activated.");
      await suspensions.reload?.();
      setReason("");
      setScopes([{ id: 0, year: "", section: "" }]);
      setNextScopeId(1);
    } catch (err: any) { toast.error(err.message || "Could not create suspension."); }
    finally { setSaving(false); setRetrying(false); }
  };
  return <Card className="mb-6"><CardHeader><CardTitle>Attendance Suspension Management</CardTitle><CardDescription>Add one scope row per year or section. Choose All Sections to suspend the entire academic year. Dates use Asia/Kolkata.</CardDescription></CardHeader><CardContent className="space-y-4">
    <div className="space-y-3">
      {scopes.map((scope, index) => <SuspensionScopeRow key={scope.id} years={yearsData.data?.years || []} scope={scope} onChange={(next) => setScopes((prev) => prev.map((item) => item.id === scope.id ? next : item))} onRemove={() => setScopes((prev) => prev.length > 1 ? prev.filter((item) => item.id !== scope.id) : prev)} canRemove={scopes.length > 1} index={index} />)}
      <Button type="button" variant="outline" size="sm" onClick={() => { setScopes((prev) => [...prev, { id: nextScopeId, year: "", section: "" }]); setNextScopeId((id) => id + 1); }}><Plus className="mr-2 size-4" />Add year or section</Button>
    </div>
    <div className="grid gap-3 md:grid-cols-2"><div className="space-y-1"><Label>Suspension type</Label><select className="h-10 w-full rounded-md border bg-background px-3" value={type} onChange={(e) => setType(e.target.value)}><option value="STUDENT">Student Attendance</option><option value="FACULTY">Faculty Attendance</option><option value="BOTH">Both</option></select></div><div className="space-y-1"><Label>Start date</Label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div><div className="space-y-1"><Label>End date</Label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div><div className="space-y-1 md:col-span-2"><Label>Optional reason</Label><Input value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} /></div></div>
    <div className="space-y-1"><Button onClick={activate} disabled={saving || yearsData.loading}>{saving ? retrying ? "Reconnecting…" : "Activating…" : "Activate suspension"}</Button>{saving && retrying && <p className="text-xs text-muted-foreground" aria-live="polite">The backend is waking up. Retrying safely; please keep this page open.</p>}</div>
    <div className="space-y-2">{(suspensions.data || []).map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm"><div><strong>{item.status}</strong> · {item.attendance_type} · {item.years.map((year) => `${year}: ${item.all_sections_years.includes(year) ? "all sections" : (item.sections_by_year[year] || []).join(", ")}`).join("; ")} · {item.start_date} to {item.end_date}{item.reason ? ` · ${item.reason}` : ""}</div>{item.status === "ACTIVE" || item.status === "SCHEDULED" ? <Button variant="outline" size="sm" onClick={async () => { if (!window.confirm("Cancel this attendance suspension?")) return; try { await cancelAttendanceSuspension(item.id); await suspensions.reload?.(); toast.success("Suspension cancelled."); } catch (err: any) { toast.error(err.message || "Could not cancel suspension."); } }}>Cancel</Button> : null}</div>)}</div>
  </CardContent></Card>;
}

function SuspensionScopeRow({ years, scope, onChange, onRemove, canRemove, index }: { years: string[]; scope: { id: number; year: string; section: string }; onChange: (scope: { id: number; year: string; section: string }) => void; onRemove: () => void; canRemove: boolean; index: number }) {
  const sectionData = useAsyncData<Section[]>(() => scope.year ? getSections(scope.year, undefined, true) : Promise.resolve([]), [scope.year]);
  const options = [...new Map((sectionData.data || []).map((item) => [item.sectionName.trim().toUpperCase(), item.sectionName.trim()])).values()];
  return <div className="grid items-end gap-3 rounded-lg border bg-muted/20 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
    <div className="min-w-0 space-y-1.5"><Label htmlFor={`suspension-year-${scope.id}`}>Academic year {index + 1}</Label><select id={`suspension-year-${scope.id}`} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={scope.year} onChange={(event) => onChange({ ...scope, year: event.target.value, section: "" })}><option value="">Select academic year</option>{years.map((year) => <option key={year} value={year}>{year}</option>)}</select></div>
    <div className="min-w-0 space-y-1.5"><Label htmlFor={`suspension-section-${scope.id}`}>Section(s)</Label><select id={`suspension-section-${scope.id}`} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={scope.section} disabled={!scope.year || sectionData.loading} onChange={(event) => onChange({ ...scope, section: event.target.value })}><option value="">Select a section</option><option value="__ALL_SECTIONS__">All sections in this year</option>{options.map((section) => <option key={section} value={section}>{section}</option>)}</select></div>
    {canRemove && <Button type="button" variant="ghost" size="icon" aria-label="Remove year and section" onClick={onRemove}><Trash2 className="size-4" /></Button>}
  </div>;
}
