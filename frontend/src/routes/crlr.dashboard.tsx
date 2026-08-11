import { createFileRoute, Link } from "@tanstack/react-router";
import { CalendarClock, Clock, Repeat2, UserCheck, UserX } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getSessions } from "@/services/sessionService";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/crlr/dashboard")({
  head: () => ({
    meta: [
      { title: "CR/LR Dashboard — Faculty Attendance Monitor" },
      { name: "description", content: "Today's sessions, pending faculty confirmations and recent responses for your section." },
      { property: "og:title", content: "CR/LR Dashboard — Faculty Attendance Monitor" },
      { property: "og:description", content: "Today's sessions and pending faculty confirmations for your section." },
    ],
  }),
  component: CRLRDashboardPage,
});

function CRLRDashboardPage() {
  const { user } = useAuth();
  const section = user?.section ?? "";
  const { data, loading, error, reload } = useAsyncData(() => getSessions(section), [section]);

  const sessions = data ?? [];
  const pending = sessions.filter((s) => s.facultyResponse === "Pending").length;
  const present = sessions.filter((s) => s.facultyResponse === "Present").length;
  const absent = sessions.filter((s) => s.facultyResponse === "Not Present").length;
  const substitute = sessions.filter((s) => s.facultyResponse === "Substitute").length;
  const responded = sessions.filter((s) => s.facultyResponse !== "Pending");

  return (
    <CRLRLayout>
      <PageHeader
        title="Dashboard"
        description={`Section ${section} — today's faculty attendance overview`}
        actions={
          <Button asChild size="sm">
            <Link to="/crlr/attendance">Open Attendance</Link>
          </Button>
        }
      />

      {loading ? (
        <LoadingState rows={4} label="Loading your sessions..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : (
        <>
          <section className="grid gap-3 grid-cols-2 lg:grid-cols-3">
            <StatCard label="Today's Sessions" value={sessions.length} icon={CalendarClock} />
            <StatCard label="Pending Confirmations" value={pending} icon={Clock} tone="warning" />
            <StatCard label="Faculty Present" value={present} icon={UserCheck} tone="success" />
            <StatCard label="Faculty Absent" value={absent} icon={UserX} tone="destructive" />
            <StatCard label="Substitute" value={substitute} icon={Repeat2} tone="info" />
          </section>

          <section className="space-y-3">
            <h2 className="text-base font-semibold">Recent Responses</h2>
            {responded.length === 0 ? (
              <EmptyState
                title="No responses yet"
                description="Your submitted faculty attendance responses will appear here."
              />
            ) : (
              <div className="space-y-3">
                {responded.map((s) => (
                  <Card key={s.id}>
                    <CardContent className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-4">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{s.subject}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {s.period} · {s.startTime} - {s.endTime}
                          {s.responseTime ? ` · responded ${s.responseTime}` : ""}
                          {s.substituteName ? ` · ${s.substituteName}` : ""}
                        </p>
                      </div>
                      <StatusBadge status={s.facultyResponse} />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </CRLRLayout>
  );
}
