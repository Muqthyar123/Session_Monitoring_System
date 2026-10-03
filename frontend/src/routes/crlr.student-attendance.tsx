import { useMemo, useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, UserX, Search, Send, GraduationCap, Calendar, Lock, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useAuth } from "@/context/AuthContext";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getCRLRStudents,
  getCRLRSubmissionStatus,
  submitStudentAttendance,
} from "@/services/studentAttendanceService";
import { getSessions } from "@/services/sessionService";

export const Route = createFileRoute("/crlr/student-attendance")({
  head: () => ({
    meta: [
      { title: "Provide Student Attendance — CR/LR Portal" },
      { name: "description", content: "Mark daily student attendance for your assigned class section." },
    ],
  }),
  component: CRLRStudentAttendancePage,
});

function CRLRStudentAttendancePage() {
  const { user } = useAuth();
  const isSunday = new Date().getDay() === 0;

  const { data: todaySessions } = useAsyncData(
    () => (user?.section ? getSessions(user.section) : Promise.resolve([])),
    [user?.section]
  );
  const hasClassesToday = (todaySessions ?? []).length > 0;
  const showSundayNoClass = isSunday && !hasClassesToday;

  const { data: students, loading, error, reload } = useAsyncData(
    () => (showSundayNoClass ? Promise.resolve([]) : getCRLRStudents()),
    [showSundayNoClass]
  );

  // Daily Submission Status Check
  const {
    data: subStatus,
    loading: loadingStatus,
    reload: reloadStatus,
  } = useAsyncData(
    () =>
      user?.year && user?.section
        ? getCRLRSubmissionStatus(user.year, user.section)
        : Promise.resolve(null),
    [user?.year, user?.section]
  );

  const isSubmittedToday = subStatus?.isSubmittedToday ?? false;

  const [search, setSearch] = useState("");
  // Set of rollNumbers marked as ABSENT
  const [absentRolls, setAbsentRolls] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  // Auto-sync submitted absentees if attendance is already submitted
  useEffect(() => {
    if (subStatus?.isSubmittedToday && subStatus.absentRolls) {
      setAbsentRolls(new Set(subStatus.absentRolls));
    }
  }, [subStatus]);

  const filteredStudents = useMemo(() => {
    if (!students) return [];
    const term = search.trim().toLowerCase();
    if (!term) return students;
    return students.filter(
      (s) =>
        s.name.toLowerCase().includes(term) ||
        s.rollNumber.toLowerCase().includes(term)
    );
  }, [students, search]);

  const toggleAbsent = (rollNumber: string) => {
    if (isSubmittedToday) {
      toast.info("Attendance has already been submitted for today and is locked.");
      return;
    }
    setAbsentRolls((prev) => {
      const next = new Set(prev);
      if (next.has(rollNumber)) {
        next.delete(rollNumber);
      } else {
        next.add(rollNumber);
      }
      return next;
    });
  };

  const markAllPresent = () => {
    if (isSubmittedToday) {
      toast.info("Attendance has already been submitted for today and is locked.");
      return;
    }
    setAbsentRolls(new Set());
  };

  const selectedAbsentees = useMemo(() => {
    if (!students) return [];
    return students.filter((s) => absentRolls.has(s.rollNumber));
  }, [students, absentRolls]);

  const handleSubmit = async () => {
    if (showSundayNoClass) {
      toast.error("No classes are Available Due to Sunday.");
      return;
    }
    if (isSubmittedToday) {
      toast.error("Today's attendance has already been submitted and cannot be duplicated.");
      return;
    }
    if (!user?.year || !user?.section) {
      toast.error("Your login is missing assigned year or section.");
      return;
    }

    setSubmitting(true);
    try {
      const absenteesPayload = selectedAbsentees.map((s) => ({
        rollNumber: s.rollNumber,
        studentId: s.id,
        studentName: s.name,
        studentPhone: s.studentPhone,
        parentPhone: s.parentPhone,
      }));

      const res = await submitStudentAttendance({
        year: user.year,
        section: user.section,
        absentees: absenteesPayload,
      });

      toast.success(
        res.message || `Student attendance submitted successfully (${res.absent_count} absent).`
      );
      if (reloadStatus) reloadStatus();
      if (reload) reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to submit student attendance.");
      if (reloadStatus) reloadStatus();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <CRLRLayout>
      <PageHeader
        title="Provide Student Attendance"
        description={`Mark absent students for ${user?.year || "Year"} — Section ${user?.section || "Section"}. All others will be marked Present.`}
      />

      {showSundayNoClass ? (
        <Card className="border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 p-8 text-center my-4">
          <div className="flex flex-col items-center justify-center gap-3">
            <Calendar className="size-10 text-amber-600 dark:text-amber-400" />
            <h3 className="text-xl font-bold">No class are Available Due to Sunday</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Today is Sunday. Student attendance submission is disabled as no classes are scheduled.
            </p>
          </div>
        </Card>
      ) : (
        <>
          {/* Already Submitted Warning Banner */}
          {isSubmittedToday && (
            <Card className="border-emerald-500/30 bg-emerald-50/70 dark:bg-emerald-950/30">
              <CardContent className="flex items-center gap-3 py-3.5">
                <div className="rounded-full bg-emerald-500/20 p-2 text-emerald-700 dark:text-emerald-300 shrink-0">
                  <CheckCircle2 className="size-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                    Today's Attendance Submitted & Locked
                  </p>
                  <p className="text-xs text-emerald-800 dark:text-emerald-300/80">
                    Attendance for {user?.year} Section {user?.section} was submitted by{" "}
                    <strong>{subStatus?.submittedBy}</strong>
                    {subStatus?.submittedAt ? ` on ${new Date(subStatus.submittedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ""}{" "}
                    ({subStatus?.absentCount ?? 0} absentees recorded). Submissions reset tomorrow.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Info Banner */}
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-primary/10 p-2.5 text-primary">
                  <GraduationCap className="size-6" />
                </div>
                <div>
                  <p className="font-semibold text-sm">Assigned Class Section</p>
                  <p className="text-xs text-muted-foreground">
                    {user?.year} &bull; Section {user?.section} &bull; Logged in as: {user?.name} ({user?.role})
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm font-medium">
                <div className="flex items-center gap-1.5 text-emerald-600">
                  <CheckCircle2 className="size-4" />
                  <span>Present: {(students?.length || 0) - absentRolls.size}</span>
                </div>
                <div className="flex items-center gap-1.5 text-rose-600">
                  <UserX className="size-4" />
                  <span>Absent: {absentRolls.size}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Student Selection Table / List */}
            <Card className="lg:col-span-2">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    Class Roll Call
                    {isSubmittedToday && (
                      <Badge variant="outline" className="gap-1 border-emerald-500 text-emerald-700 dark:text-emerald-400 text-[10px]">
                        <Lock className="size-3" /> Submitted Record
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>
                    {isSubmittedToday
                      ? "Today's attendance has been recorded and is displayed below."
                      : "Check the box next to a student to mark them as ABSENT today."}
                  </CardDescription>
                </div>
                {!isSubmittedToday && (
                  <Button variant="outline" size="sm" onClick={markAllPresent}>
                    Mark All Present
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search by student name or roll number..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>

                {loading || loadingStatus ? (
                  <LoadingState label="Loading section students..." />
                ) : error ? (
                  <ErrorState title="Failed to load students" description={error.message} retry={reload} />
                ) : !students || students.length === 0 ? (
                  <EmptyState
                    title="No students found in section"
                    description={`No students are registered under ${user?.year} Section ${user?.section}. Admin needs to add students.`}
                  />
                ) : filteredStudents.length === 0 ? (
                  <EmptyState
                    title="No matching student"
                    description="No student matches your search query."
                  />
                ) : (
                  <div className="divide-y rounded-md border">
                    {filteredStudents.map((s) => {
                      const isAbsent = absentRolls.has(s.rollNumber);
                      return (
                        <div
                          key={s.id}
                          onClick={() => toggleAbsent(s.rollNumber)}
                          className={`flex items-center justify-between p-3.5 transition-colors ${
                            isSubmittedToday ? "cursor-default" : "cursor-pointer"
                          } ${
                            isAbsent ? "bg-rose-500/10 dark:bg-rose-950/20" : "hover:bg-muted/50"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={isAbsent}
                              disabled={isSubmittedToday}
                              onCheckedChange={() => toggleAbsent(s.rollNumber)}
                              className="size-5 border-rose-500 data-[state=checked]:bg-rose-600 data-[state=checked]:text-white"
                            />
                            <div>
                              <p className="font-semibold text-sm">{s.name}</p>
                              <p className="font-mono text-xs text-muted-foreground">
                                {s.rollNumber}
                              </p>
                            </div>
                          </div>

                          <div>
                            {isAbsent ? (
                              <Badge variant="destructive" className="gap-1">
                                <UserX className="size-3" /> ABSENT
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="gap-1 border-emerald-500/40 text-emerald-600">
                                <CheckCircle2 className="size-3" /> PRESENT
                              </Badge>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Absentee Summary & Submit */}
            <Card className="h-fit">
              <CardHeader>
                <CardTitle>Attendance Submission Summary</CardTitle>
                <CardDescription>
                  {isSubmittedToday
                    ? "Summary of recorded attendance for today."
                    : "Review absent students before submitting daily record."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border p-4 text-center space-y-1">
                  <p className="text-2xl font-bold">{absentRolls.size}</p>
                  <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                    Students Marked Absent
                  </p>
                </div>

                {selectedAbsentees.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase">
                      Absentee Roster ({selectedAbsentees.length}):
                    </p>
                    <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                      {selectedAbsentees.map((s) => (
                        <div
                          key={s.id}
                          className="flex items-center justify-between rounded-md bg-rose-500/10 p-2 text-xs"
                        >
                          <span className="font-medium text-rose-700 dark:text-rose-400">
                            {s.name}
                          </span>
                          <span className="font-mono text-muted-foreground">{s.rollNumber}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-md bg-emerald-500/10 p-3 text-center text-xs text-emerald-700 dark:text-emerald-400">
                    100% Attendance — All students marked Present!
                  </div>
                )}

                {isSubmittedToday ? (
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-600 cursor-not-allowed opacity-90 text-white"
                    size="lg"
                    disabled
                  >
                    <CheckCircle2 className="size-4 mr-2" />
                    Attendance Already Submitted for Today
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    size="lg"
                    onClick={handleSubmit}
                    disabled={submitting || !students || students.length === 0}
                  >
                    <Send className="size-4 mr-2" />
                    {submitting ? "Submitting..." : "Submit Attendance Record"}
                  </Button>
                )}

                {isSubmittedToday && (
                  <p className="text-[11px] text-center text-muted-foreground">
                    Only one attendance submission is permitted per section each day. Next submission opens tomorrow.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </CRLRLayout>
  );
}

