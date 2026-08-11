import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { AttendanceForm } from "@/components/sessions/AttendanceForm";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
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
  const active = sessions.filter((s) => s.sessionStatus === "Active");
  const upcoming = sessions.filter((s) => s.sessionStatus === "Upcoming");

  return (
    <CRLRLayout>
      <PageHeader
        title="Faculty Attendance"
        description={`Section ${section} — respond to the active session`}
      />

      {loading ? (
        <LoadingState rows={3} label="Loading your session..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No active sessions"
          description="There are no sessions requiring your response right now."
          icon={CalendarClock}
        />
      ) : (
        <div className="space-y-6">
          {active.length === 0 ? (
            <EmptyState
              title="No active session"
              description="There are no sessions requiring your response right now."
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

          {upcoming.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-base font-semibold">Upcoming Sessions</h2>
              <p className="text-xs text-muted-foreground">
                Continuous periods are grouped by the backend into a single session, so only one
                response is required for the whole block.
              </p>
              {upcoming.map((s) => (
                <Card key={s.id}>
                  <CardContent className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 p-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{s.subject}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {s.period} · {s.startTime} - {s.endTime}
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
