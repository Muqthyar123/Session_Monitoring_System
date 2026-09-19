import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Calendar, Clock, MapPin, User, Info } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getTimetable } from "@/services/timetableService";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/crlr/timetable")({
  head: () => ({
    meta: [
      { title: "Class Timetable — CR/LR Portal" },
      { name: "description", content: "View day-wise class periods, subjects, assigned faculty and room numbers for your section." },
      { property: "og:title", content: "Class Timetable — CR/LR Portal" },
      { property: "og:description", content: "Day-wise period schedule uploaded by administrator." },
    ],
  }),
  component: CRLRTimetablePage,
});

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function CRLRTimetablePage() {
  const { user } = useAuth();
  const year = user?.year ?? "";
  const section = user?.section ?? "";

  // Get current day of week (0 = Sunday, 1 = Monday, ...)
  const currentDayIndex = new Date().getDay();
  const defaultDay = currentDayIndex >= 1 && currentDayIndex <= 6 ? DAYS[currentDayIndex - 1] : "Monday";
  const [selectedDay, setSelectedDay] = useState<string>(defaultDay!);

  const { data, loading, error, reload } = useAsyncData(
    () => getTimetable(year, section),
    [year, section]
  );

  const timetablePeriods = data ?? [];
  const dayPeriods = timetablePeriods
    .filter((p) => p && p.day && p.day.toLowerCase() === selectedDay.toLowerCase())
    .sort((a, b) => (a.period || 0) - (b.period || 0));

  return (
    <CRLRLayout>
      <PageHeader
        title="Class Timetable"
        description={`Section ${section} — day-wise class schedule and assigned faculty`}
      />

      <div className="flex flex-wrap gap-2 pb-2">
        {DAYS.map((d) => (
          <Button
            key={d}
            variant={selectedDay === d ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedDay(d)}
            className="capitalize"
          >
            {d}
            {d === defaultDay ? <Badge variant="secondary" className="ml-1 text-[10px]">Today</Badge> : null}
          </Button>
        ))}
      </div>

      <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3.5 text-xs text-blue-900 dark:border-blue-950 dark:bg-blue-950/30 dark:text-blue-200 flex items-start gap-2.5">
        <Info className="size-4 shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" />
        <div>
          <p className="font-semibold">Automated Continuous Session Merging</p>
          <p className="text-muted-foreground mt-0.5">
            When multiple consecutive periods have the same subject and faculty, the backend combines them into a single continuous class session. Only 1 attendance notification is generated for the combined block.
          </p>
        </div>
      </div>

      {loading ? (
        <LoadingState rows={4} label="Loading timetable..." />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : dayPeriods.length === 0 ? (
        <EmptyState
          title={`No classes scheduled for ${selectedDay}`}
          description={`No timetable periods uploaded for section ${section} on ${selectedDay}.`}
          icon={Calendar}
        />
      ) : (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center justify-between">
              <span>{selectedDay} Schedule</span>
              <Badge variant="outline" className="font-mono text-xs font-normal">
                {dayPeriods.length} {dayPeriods.length === 1 ? "Period" : "Periods"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {dayPeriods.map((p) => (
              <div
                key={p.period}
                className="grid grid-cols-1 md:grid-cols-[100px_minmax(0,1fr)_auto] gap-3 items-center rounded-lg border p-3.5 bg-card hover:bg-secondary/40 transition-colors"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                  <Clock className="size-3.5" />
                  <span>Period {p.period}</span>
                </div>

                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">{p.subject}</p>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" /> {p.startTime} - {p.endTime}
                    </span>
                    {p.faculty ? (
                      <span className="flex items-center gap-1 font-medium text-foreground/80">
                        <User className="size-3" /> {p.faculty}
                      </span>
                    ) : null}
                    {p.room ? (
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <MapPin className="size-3" /> Room: {p.room}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div>
                  <Badge variant="secondary" className="text-xs">
                    {p.startTime} - {p.endTime}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </CRLRLayout>
  );
}
