import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Calendar, Info } from "lucide-react";
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

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function CRLRTimetablePage() {
  const { user } = useAuth();
  const year = user?.year ?? "";
  const section = user?.section ?? "";

  // Get current real-time day of week (0 = Sunday, 1 = Monday, ..., 6 = Saturday)
  const currentDayIndex = new Date().getDay();
  const todayName = DAY_NAMES[currentDayIndex];
  const [selectedDay, setSelectedDay] = useState<string>(todayName || "Monday");

  const { data, loading, error, reload } = useAsyncData(
    () => getTimetable(year, section),
    [year, section]
  );

  const timetablePeriods = data ?? [];
  const dayPeriods = timetablePeriods
    .filter((p) => p && p.day && p.day.toLowerCase() === selectedDay.toLowerCase())
    .sort((a, b) => (a.period || 0) - (b.period || 0));

  const isSelectedSunday = selectedDay === "Sunday";

  return (
    <CRLRLayout>
      <PageHeader
        title="Class Timetable"
        description={`Section ${section} — day-wise class schedule and assigned faculty`}
      />

      {/* Real-time Day Navigation Tabs with "Today" Badge */}
      <div className="flex flex-wrap gap-2 pb-2">
        {DAYS.map((d) => {
          const isToday = d === todayName;
          const isSelected = selectedDay === d;
          return (
            <Button
              key={d}
              variant={isSelected ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedDay(d)}
              className="capitalize flex items-center gap-1.5"
            >
              <span>{d}</span>
              {isToday ? (
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-[11px] leading-none transition-colors",
                    isSelected
                      ? "bg-white text-primary font-bold shadow-xs"
                      : "bg-primary text-primary-foreground font-medium"
                  )}
                >
                  Today
                </span>
              ) : null}
            </Button>
          );
        })}
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
      ) : isSelectedSunday && dayPeriods.length === 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 p-8 text-center my-4">
          <div className="flex flex-col items-center justify-center gap-3">
            <Calendar className="size-10 text-amber-600 dark:text-amber-400" />
            <h3 className="text-xl font-bold">No class are Available Due to Sunday</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Sunday is an official weekly holiday. Regular classes resume on Monday.
            </p>
          </div>
        </Card>
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
            {dayPeriods.map((period) => (
              <div
                key={`${period.day}-${period.period}`}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg border bg-card hover:bg-muted/40 transition-colors gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="font-mono text-xs">
                      Period {period.period}
                    </Badge>
                    <span className="font-bold text-sm">{period.subject}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground pt-0.5">
                    <span>Faculty: <strong className="text-foreground">{period.faculty || "TBD"}</strong></span>
                    <span>Room: <strong className="text-foreground">{period.room || "TBD"}</strong></span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-mono text-xs font-semibold text-primary">
                    {period.startTime} - {period.endTime}
                  </span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </CRLRLayout>
  );
}
