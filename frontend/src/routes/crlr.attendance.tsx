import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock, Calendar } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { AttendanceForm } from "@/components/sessions/AttendanceForm";
import { Card } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getActiveSessions } from "@/services/sessionService";
import { useAuth } from "@/context/AuthContext";
import { getAttendanceControlStatus } from "@/services/studentAttendanceService";
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
  const [suspended, setSuspended] = useState(false);
  const [suspensionMessage, setSuspensionMessage] = useState("");
  const attendanceDate = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

  useEffect(() => {
    if (!user?.year || !section) return;
    const refresh = () => getAttendanceControlStatus(user.year!, section, attendanceDate, "SESSION_1", "FACULTY")
      .then((control) => {
        setSuspended(control.suspended);
        setSuspensionMessage(control.suspensions.map((x) => `${x.startDate} through ${x.endDate}${x.reason ? ` — ${x.reason}` : ""}`).join(" · "));
      }).catch(() => {});
    void refresh();
    const timer = window.setInterval(refresh, 15000);
    return () => window.clearInterval(timer);
  }, [user?.year, section, attendanceDate]);

  const isSunday = new Date().getDay() === 0;

  const { data, loading, error, reload } = useAsyncData(
    () => getActiveSessions(section),
    [section],
    3000
  );
  const [overrides, setOverrides] = useState<Record<string, ClassSession>>({});

  const getMinPeriod = (s: ClassSession) => {
    if (s.periodsIncluded && s.periodsIncluded.length > 0) {
      return Math.min(...s.periodsIncluded);
    }
    const match = s.period?.match(/\d+/);
    return match ? parseInt(match[0], 10) : 99;
  };

  // Sort all sessions for today strictly in Period-wise order
  const sessions = (data ?? [])
    .map((s) => {
      const sid = s.id || (s as any)._id;
      return (sid ? overrides[sid] : null) ?? s;
    })
    .sort((a, b) => getMinPeriod(a) - getMinPeriod(b));

  return (
    <CRLRLayout>
      <PageHeader
        title="Faculty Attendance"
        description={`Section ${section} — period-wise faculty attendance portal`}
      />

      {suspended && <Card className="my-4 border-amber-500/40 bg-amber-50/70 p-4 dark:bg-amber-950/20"><p className="font-semibold">Faculty attendance is suspended</p><p className="text-sm text-muted-foreground">{suspensionMessage}</p></Card>}

      {loading ? (
        <LoadingState rows={3} label="Loading class schedule..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : isSunday && sessions.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 p-8 text-center my-4">
          <div className="flex flex-col items-center justify-center gap-3">
            <Calendar className="size-10 text-amber-600 dark:text-amber-400" />
            <h3 className="text-xl font-bold">No class are Available Due to Sunday</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Today is Sunday. Faculty attendance marking is disabled as no classes are scheduled.
            </p>
          </div>
        </Card>
      ) : suspended ? (
        <EmptyState title="Attendance marking is suspended" description="Your scheduled sessions remain available in history after the suspension ends." icon={CalendarClock} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions scheduled for today"
          description="There are no class sessions scheduled for your section today."
          icon={CalendarClock}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sessions.map((session) => {
            const sid = session.id || (session as any)._id || session.period;
            return (
              <AttendanceForm
                key={sid}
                session={session}
                onSubmitted={(updated) => {
                  const updatedId = updated.id || (updated as any)._id;
                  if (updatedId) {
                    setOverrides((prev) => ({ ...prev, [updatedId]: updated }));
                  }
                }}
              />
            );
          })}
        </div>
      )}
    </CRLRLayout>
  );
}
