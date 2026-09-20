import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock, CheckCircle2, Lock, UserX } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { AttendanceForm } from "@/components/sessions/AttendanceForm";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
    [section]
  );
  const [overrides, setOverrides] = useState<Record<string, ClassSession>>({});

  const getMinPeriod = (s: ClassSession) => {
    if (s.periodsIncluded && s.periodsIncluded.length > 0) {
      return Math.min(...s.periodsIncluded);
    }
    const match = s.period?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 99;
  };

  const sessions = (data ?? [])
    .map((s) => overrides[s.id] ?? s)
    .sort((a, b) => getMinPeriod(a) - getMinPeriod(b));

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
          {/* Active Class Sessions Section */}
          {active.length === 0 ? (
            <EmptyState
              title="No active class session right now"
              description="Faculty attendance marking is active right when scheduled class period starts (e.g., 09:10 AM, 10:00 AM, etc.). Active periods unlock automatically when class begins."
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

          {/* Completed Class Sessions */}
          {completed.length > 0 ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Completed Class Hours</h2>
                <Badge variant="outline" className="text-xs font-normal">
                  {completed.length} Completed
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Class hours for these periods are finished or responded. Attendance details are recorded in unselected read-only state.
              </p>
              <div className="space-y-4">
                {completed.map((s) => (
                  <Card key={s.id} className="bg-muted/20 border-border opacity-90 hover:opacity-100 transition-opacity">
                    <CardContent className="flex flex-col justify-between p-4 h-full space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-bold text-foreground">
                            {s.subject} {s.faculty ? `— ${s.faculty}` : ""}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5 font-medium">
                            {s.period} · {s.startTime} - {s.endTime}
                          </p>
                        </div>
                        <StatusBadge
                          status={s.facultyResponse !== "Pending" ? s.facultyResponse : "Completed"}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground border-t border-border/50 pt-2 space-y-0.5">
                        <p className="truncate">
                          <span className="font-medium text-foreground">Faculty:</span> {s.faculty || "Assigned Faculty"}
                        </p>
                        {s.substituteName ? (
                          <p className="truncate text-primary font-medium">
                            <span>Substitute:</span> {s.substituteName}
                          </p>
                        ) : null}
                        {s.responseTime ? (
                          <p className="text-[11px] text-muted-foreground/80">
                            Responded: {s.responseTime}
                          </p>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          ) : null}

          {/* Upcoming Class Sessions (Disabled Attendance Controls until Start Time) */}
          {upcoming.length > 0 ? (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Upcoming Class Hours</h2>
                <Badge variant="secondary" className="text-xs font-normal">
                  {upcoming.length} Upcoming
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Attendance marking is disabled for these periods. Controls will unlock automatically right when each period starts.
              </p>
              <div className="space-y-4">
                {upcoming.map((s) => (
                  <Card key={s.id} className="border-border">
                    <CardContent className="flex flex-col justify-between p-4 h-full space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-bold text-foreground">
                            {s.subject} {s.faculty ? `— ${s.faculty}` : ""}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5 font-medium">
                            {s.period} · {s.startTime} - {s.endTime}
                          </p>
                        </div>
                        <StatusBadge status={s.sessionStatus} />
                      </div>

                      <div className="flex flex-col space-y-3 border-t border-border/50 pt-2">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <p className="truncate">
                            <span className="font-medium text-foreground">Faculty:</span> {s.faculty || "Assigned Faculty"}
                          </p>
                          <span className="inline-flex items-center gap-1 rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:text-slate-400">
                            <Lock className="size-3 text-slate-400" />
                            Unlocks at {s.startTime}
                          </span>
                        </div>

                        {/* Disabled Attendance Marking Option until Period Start Time */}
                        <div className="grid gap-3 sm:grid-cols-2 pt-1 opacity-60">
                          <Button size="sm" disabled className="w-full cursor-not-allowed">
                            <CheckCircle2 className="size-4" /> Faculty Present (Disabled)
                          </Button>
                          <Button size="sm" variant="outline" disabled className="w-full cursor-not-allowed">
                            <UserX className="size-4" /> Faculty Not Present (Disabled)
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </CRLRLayout>
  );
}
