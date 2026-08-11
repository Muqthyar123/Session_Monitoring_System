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
import { Percent, Repeat2, UserCheck, UserX } from "lucide-react";
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
      { title: "Section Analytics — CR/LR Portal" },
      { name: "description", content: "Faculty presence, absence, substitute and response-rate analytics for your assigned section." },
      { property: "og:title", content: "Section Analytics — CR/LR Portal" },
      { property: "og:description", content: "Faculty presence and response analytics for your section." },
    ],
  }),
  component: CRLRAnalyticsPage,
});

const PIE_COLORS = ["var(--color-chart-2)", "var(--color-chart-3)", "var(--color-chart-4)"];

function CRLRAnalyticsPage() {
  const { user } = useAuth();
  const section = user?.section ?? "";
  const { data, loading, error, reload } = useAsyncData(() => getCRLRAnalytics(section), [section]);

  return (
    <CRLRLayout>
      <PageHeader title="Analytics" description={`Section ${section} only`} />

      {loading ? (
        <LoadingState rows={4} label="Loading analytics..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : data ? (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Faculty Present" value={data.summary.facultyPresent} icon={UserCheck} tone="success" />
            <StatCard label="Faculty Absent" value={data.summary.facultyAbsent} icon={UserX} tone="destructive" />
            <StatCard label="Substitute" value={data.summary.substitute} icon={Repeat2} tone="info" />
            <StatCard label="Response Rate" value={`${data.summary.responseRate}%`} icon={Percent} />
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
                    {data.responseStatus.map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      ) : null}
    </CRLRLayout>
  );
}
