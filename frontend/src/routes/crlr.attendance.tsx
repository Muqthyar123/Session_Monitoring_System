import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { AttendanceForm } from "@/components/sessions/AttendanceForm";
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

  // Sort all sessions for today strictly in Period-wise order (Period 1, Period 2, ...)
  const sessions = (data ?? [])
    .map((s) => overrides[s.id] ?? s)
    .sort((a, b) => getMinPeriod(a) - getMinPeriod(b));

  return (
    <CRLRLayout>
      <PageHeader
        title="Faculty Attendance"
        description={`Section ${section} — period-wise faculty attendance portal`}
      />

      {loading ? (
        <LoadingState rows={3} label="Loading class schedule..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : sessions.length === 0 ? (
        <EmptyState
          title="No sessions scheduled for today"
          description="There are no class sessions scheduled for your section today."
          icon={CalendarClock}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sessions.map((session) => (
            <AttendanceForm
              key={session.id}
              session={session}
              onSubmitted={(updated) =>
                setOverrides((prev) => ({ ...prev, [updated.id]: updated }))
              }
            />
          ))}
        </div>
      )}
    </CRLRLayout>
  );
}
