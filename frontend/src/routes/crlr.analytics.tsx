import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  GraduationCap,
  Percent,
  Repeat2,
  Search,
  UserCheck,
  UserX,
  XCircle,
} from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { ChartCard } from "@/components/common/ChartCard";
import { ErrorState, LoadingState } from "@/components/common/States";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getCRLRAnalytics } from "@/services/sessionService";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/crlr/analytics")({
  head: () => ({
    meta: [
      { title: "Faculty Analytics — CR/LR Portal" },
      { name: "description", content: "Faculty presence, absence, substitute, assigned hours, and response-rate analytics for your assigned section." },
      { property: "og:title", content: "Faculty Analytics — CR/LR Portal" },
      { property: "og:description", content: "Faculty presence and response analytics for your section." },
    ],
  }),
  component: CRLRAnalyticsPage,
});

const PIE_COLORS = ["var(--color-chart-2)", "var(--color-chart-3)", "var(--color-chart-4)"];

interface FacultyAnalyticsItem {
  facultyName: string;
  subject: string;
  section: string;
  totalHours: number;
  attendedHours: number;
  absentHours: number;
  substitutedHours: number;
  attendancePercentage: number;
}

function CRLRAnalyticsPage() {
  const { user } = useAuth();
  const section = user?.section ?? "";
  const { data, loading, error, reload } = useAsyncData(() => getCRLRAnalytics(section), [section]);
  const [searchQuery, setSearchQuery] = useState("");

  const facultyList: FacultyAnalyticsItem[] = data?.facultyAnalytics ?? [];

  const filteredFaculty = facultyList.filter(
    (item) =>
      item.facultyName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.subject.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <CRLRLayout>
      <PageHeader title="Faculty Attendance Analytics" description={`Section ${section} — Per-Faculty Attendance Analysis`} />

      {loading ? (
        <LoadingState rows={4} label="Loading analytics..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : data ? (
        <div className="space-y-6">
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Faculty Present" value={data.summary.facultyPresent} icon={UserCheck} tone="success" />
            <StatCard label="Faculty Absent" value={data.summary.facultyAbsent} icon={UserX} tone="destructive" />
            <StatCard label="Substitute" value={data.summary.substitute} icon={Repeat2} tone="info" />
            <StatCard label="Response Rate" value={`${data.summary.responseRate}%`} icon={Percent} />
          </section>

          {/* Detailed Faculty Attendance Analysis Section */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
                  <GraduationCap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                  Faculty Attendance Analysis
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Individual breakdown of total assigned classes, attended, absent, and substituted classes.
                </p>
              </div>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search faculty or subject..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-9 pr-3 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-800 dark:bg-slate-950 dark:text-white"
                />
              </div>
            </div>

            {filteredFaculty.length === 0 ? (
              <div className="my-8 text-center text-sm text-slate-500 dark:text-slate-400">
                No faculty members found matching your search.
              </div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-700 dark:text-slate-300">
                  <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
                    <tr>
                      <th className="px-4 py-3">Faculty Member</th>
                      <th className="px-4 py-3">Subject(s)</th>
                      <th className="px-4 py-3 text-center">Total Classes</th>
                      <th className="px-4 py-3 text-center">Attended (Present)</th>
                      <th className="px-4 py-3 text-center">Absent</th>
                      <th className="px-4 py-3 text-center">Substituted</th>
                      <th className="px-4 py-3 text-right">Attendance %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {filteredFaculty.map((fac, idx) => {
                      const pct = fac.attendancePercentage;
                      const badgeColor =
                        pct >= 85
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                          : pct >= 70
                          ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                          : "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400";

                      const barColor =
                        pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-rose-500";

                      const totalCls = (fac as any).totalClasses ?? fac.totalHours;
                      const attCls = (fac as any).attendedClasses ?? fac.attendedHours;
                      const absCls = (fac as any).absentClasses ?? fac.absentHours;
                      const subCls = (fac as any).substitutedClasses ?? fac.substitutedHours;

                      return (
                        <tr
                          key={`${fac.facultyName}-${idx}`}
                          className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40"
                        >
                          <td className="px-4 py-3.5 font-medium text-slate-900 dark:text-white">
                            <div className="flex items-center gap-2">
                              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-50 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                                {fac.facultyName.charAt(0).toUpperCase()}
                              </div>
                              <span>{fac.facultyName}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                              <BookOpen className="h-3.5 w-3.5 text-slate-400" />
                              <span>{fac.subject}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-center font-semibold text-slate-900 dark:text-white">
                            <div className="inline-flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5 text-slate-400" />
                              <span>{totalCls} classes</span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              {attCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                              <XCircle className="h-3.5 w-3.5" />
                              {absCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-400">
                              <Repeat2 className="h-3.5 w-3.5" />
                              {subCls} classes
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 rounded-full bg-slate-100 dark:bg-slate-800">
                                <div
                                  className={`h-1.5 rounded-full ${barColor}`}
                                  style={{ width: `${Math.min(100, pct)}%` }}
                                />
                              </div>
                              <span
                                className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold ${badgeColor}`}
                              >
                                {pct}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <ChartCard title="Daily Faculty Presence" description="Current week">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="present" name="Present" fill="var(--color-chart-2)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="absent" name="Absent" fill="var(--color-chart-4)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="substitute" name="Substitute" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Weekly Faculty Presence" description="Presence percentage by week">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.weekly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="week" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="presencePercent"
                    name="Presence %"
                    stroke="var(--color-chart-1)"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Session Response Status" description="Your responses this month">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.responseStatus}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    isAnimationActive={false}
                  >
                    {data.responseStatus.map((entry: any, index: number) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </div>
      ) : null}
    </CRLRLayout>
  );
}
