import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Calendar, Clock, MapPin, User, Info, ClipboardCheck } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getTimetable } from "@/services/timetableService";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

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

function getPeriodTimeStatus(
  selectedDay: string,
  defaultDay: string,
  startTimeStr: string,
  endTimeStr: string
): "active" | "completed" | "upcoming" {
  const selIdx = DAYS.indexOf(selectedDay);
  const defIdx = DAYS.indexOf(defaultDay);

  if (selIdx < defIdx) return "completed";
  if (selIdx > defIdx) return "upcoming";

  // Same day: Compare current time with start and end times
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  const parseMinutes = (tStr: string) => {
    if (!tStr) return 0;
    const parts = tStr.split(":");
    let h = parseInt(parts[0] || "0", 10);
    const m = parseInt(parts[1] || "0", 10);
    if (h < 8) h += 12; // Convert afternoon 12-hour format
    return h * 60 + m;
  };

  const startMin = parseMinutes(startTimeStr);
  const endMin = parseMinutes(endTimeStr);

  if (currentMinutes >= startMin && currentMinutes <= endMin + 15) {
    return "active";
  } else if (currentMinutes > endMin + 15) {
    return "completed";
  } else {
    return "upcoming";
  }
}

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
          <p className="font-semibold">Active Class Hour Attendance Marking</p>
          <p className="text-muted-foreground mt-0.5">
            Attendance marking is enabled during active class hours (09:10 AM – 04:00 PM). Completed class periods appear in unselected read-only state.
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
            {dayPeriods.map((p) => {
              const timeStatus = getPeriodTimeStatus(selectedDay, defaultDay!, p.startTime, p.endTime);
              const isActive = timeStatus === "active";
              const isCompleted = timeStatus === "completed";

              return (
                <div
                  key={p.period}
                  className={cn(
                    "grid grid-cols-1 md:grid-cols-[100px_minmax(0,1fr)_auto] gap-3 items-center rounded-lg border p-3.5 transition-colors",
                    isActive
                      ? "border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20 dark:border-emerald-800 ring-1 ring-emerald-500/30"
                      : isCompleted
                      ? "border-border bg-muted/20 opacity-80"
                      : "border-border bg-card hover:bg-secondary/40"
                  )}
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                    <Clock className="size-3.5" />
                    <span>Period {p.period}</span>
                  </div>

                  <div className="space-y-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground truncate">{p.subject}</p>
                      {isActive ? (
                        <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px]">
                          Active Class Hour
                        </Badge>
                      ) : isCompleted ? (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground border-border">
                          Class Completed
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[10px]">
                          Upcoming
                        </Badge>
                      )}
                    </div>
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

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {p.startTime} - {p.endTime}
                    </Badge>
                    {isActive ? (
                      <Button asChild size="sm" variant="default" className="shrink-0 bg-emerald-600 hover:bg-emerald-700 text-white">
                        <Link to="/crlr/attendance">
                          <ClipboardCheck className="size-3.5 mr-1" /> Mark Attendance
                        </Link>
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" disabled className="shrink-0 text-xs text-muted-foreground">
                        {isCompleted ? "Period Ended" : "Not Active Yet"}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </CRLRLayout>
  );
}
