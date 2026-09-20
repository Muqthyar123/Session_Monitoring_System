import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock, CheckCircle2, User } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { AttendanceForm } from "@/components/sessions/AttendanceForm";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getActiveSessions } from "@/services/sessionService";
import { useAuth } from "@/context/AuthContext";
import type { ClassSession } from "@/data/mock/mockData";

export const Route = createFileRoute("/crlr/attendance")({
  head: () => ({
    meta: [
      { title: "Faculty Attendance — CR/LR Portal" },
      { name: "description", content: "Report whether the assigned faculty is present for the current class session." },
      { property: "og:title", content: "Faculty Attendance — CR/LR Portal" },
      { property: "og:description", content: "Report faculty presence or a substitute faculty for the current session." },
    ],
  }),
  component: AttendancePage,
});

function AttendancePage() {
  const { user } = useAuth();
  const section = user?.section ?? "";
  const { data, loading, error, reload } = useAsyncData(
    () => getActiveSessions(section),
    [section],
  );
  const [overrides, setOverrides] = useState<Record<string, ClassSession>>({});

  const sessions = (data ?? []).map((s) => overrides[s.id] ?? s);

  // Active sessions are pending and currently within class hours
  const active = sessions.filter(
    (s) => s.sessionStatus === "Active" && s.facultyResponse === "Pending"
  );
  // Completed sessions have been answered or past class hours
  const completed = sessions.filter(
    (s) => s.sessionStatus === "Completed" || s.facultyResponse !== "Pending"
  );
  // Upcoming sessions are scheduled for later hours today
  const upcoming = sessions.filter(
    (s) => s.sessionStatus === "Upcoming" && s.facultyResponse === "Pending"
  );

  return (
    <CRLRLayout>
      <PageHeader
        title="Faculty Attendance"
        description={`Section ${section} — respond to active class sessions`}
      />

      {loading ? (
        <LoadingState rows={3} label="Loading your session..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions scheduled for today"
          description="There are no class sessions scheduled for your section today."
          icon={CalendarClock}
        />
      ) : (
        <div className="space-y-6">
          {/* Active Session Section */}
          {active.length === 0 ? (
            <EmptyState
              title="No active class session right now"
              description="Faculty attendance marking is active during scheduled class hours (e.g., 09:10 AM - 04:00 PM). Active periods appear here automatically when class begins."
              icon={CalendarClock}
            />
          ) : (
            active.map((session) => (
              <AttendanceForm
                key={session.id}
                session={session}
                onSubmitted={(updated) =>
                  setOverrides((prev) => ({ ...prev, [updated.id]: updated }))
                }
              />
            ))
          )}

          {/* Completed Sessions Section (Unselected Read-Only State) */}
          {completed.length > 0 ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Completed Class Hours</h2>
                <Badge variant="outline" className="text-xs font-normal">
                  {completed.length} Completed
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Class hours for these periods are finished. Faculty details and attendance responses are in unselected read-only state.
              </p>
              <div className="space-y-3">
                {completed.map((s) => (
                  <Card key={s.id} className="bg-muted/20 border-border opacity-85">
                    <CardContent className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-4">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-foreground">
                          {s.subject} {s.faculty ? `— ${s.faculty}` : ""}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {s.period} · {s.startTime} - {s.endTime}
                          {s.faculty ? ` · Faculty: ${s.faculty}` : ""}
                          {s.responseTime ? ` · Responded: ${s.responseTime}` : ""}
                          {s.substituteName ? ` · Substitute: ${s.substituteName}` : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge
                          status={s.facultyResponse !== "Pending" ? s.facultyResponse : "Completed"}
                        />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          ) : null}

          {/* Upcoming Sessions Section */}
          {upcoming.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-base font-semibold">Upcoming Class Hours</h2>
              <p className="text-xs text-muted-foreground">
                These sessions will become active when their scheduled class period starts.
              </p>
              {upcoming.map((s) => (
                <Card key={s.id}>
                  <CardContent className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">
                        {s.subject} {s.faculty ? `— ${s.faculty}` : ""}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {s.period} · {s.startTime} - {s.endTime}
                        {s.faculty ? ` · Faculty: ${s.faculty}` : ""}
                      </p>
                    </div>
                    <StatusBadge status={s.sessionStatus} />
                  </CardContent>
                </Card>
              ))}
            </section>
          ) : null}
        </div>
      )}
    </CRLRLayout>
  );
}
