import { useMemo, useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, UserX, Search, Send, GraduationCap, Calendar, Lock, AlertCircle, Download, Edit3, UserCheck } from "lucide-react";
import { toast } from "sonner";
import { exportToCSV } from "@/utils/exportUtils";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getCRLRStudents,
  getCRLRSubmissionStatus,
  submitStudentAttendance,
  correctStudentAttendance,
} from "@/services/studentAttendanceService";
import type { StudentItem } from "@/services/studentService";
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
    [user?.year, user?.section],
    15000
  );

  const [selectedSession, setSelectedSession] = useState<"SESSION_1" | "SESSION_2">("SESSION_1");
  const selectedWindow = subStatus?.sessions?.find((session) => session.sessionId === selectedSession);
  const isSubmittedToday = selectedWindow?.isSubmitted ?? false;
  const isWindowOpen = selectedWindow?.isOpen ?? false;

  const [search, setSearch] = useState("");
  // Set of rollNumbers marked as ABSENT
  const [absentRolls, setAbsentRolls] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  // Attendance Correction state
  const [correctionTarget, setCorrectionTarget] = useState<StudentItem | null>(null);
  const [correctionReason, setCorrectionReason] = useState("");
  const [correcting, setCorrecting] = useState(false);

  // Auto-sync submitted absentees if attendance is already submitted
  useEffect(() => {
    if (subStatus?.sessions) {
      const active = subStatus.sessions.find((session) => session.sessionId === selectedSession);
      setAbsentRolls(new Set(active?.absentRolls ?? []));
    }
  }, [subStatus, selectedSession]);

  const handleCorrectAttendance = async () => {
    if (!correctionTarget) return;
    const reasonTrimmed = correctionReason.trim();
    if (!reasonTrimmed || reasonTrimmed.length < 5) {
      toast.error("Reason is mandatory (minimum 5 characters).");
      return;
    }
    setCorrecting(true);
    try {
      await correctStudentAttendance({
        rollNumber: correctionTarget.rollNumber,
        newStatus: "Present",
        reason: reasonTrimmed,
        sessionId: selectedSession,
      });
      toast.success(`Corrected attendance for ${correctionTarget.name} to PRESENT.`);
      setAbsentRolls((prev) => {
        const next = new Set(prev);
        next.delete(correctionTarget.rollNumber);
        return next;
      });
      setCorrectionTarget(null);
      setCorrectionReason("");
      if (reloadStatus) reloadStatus();
    } catch (err: any) {
      toast.error(err.message || "Failed to correct attendance.");
    } finally {
      setCorrecting(false);
    }
  };

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
        ...(s.studentPhone ? { studentPhone: s.studentPhone } : {}),
        ...(s.parentPhone ? { parentPhone: s.parentPhone } : {}),
      }));

      const res = await submitStudentAttendance({
        year: user.year,
        section: user.section,
        sessionId: selectedSession,
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
        description={`Mark attendance for ${user?.year || "Year"} — Section ${user?.section || "Section"}. Each session is submitted separately.`}
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
          {!subStatus?.timetable?.configured ? (
            <Card className="border-amber-500/30 bg-amber-500/10"><CardContent className="py-4 text-sm text-amber-900 dark:text-amber-200">{subStatus?.timetable?.reason || "Timetable configuration needs attention before attendance can be marked."}</CardContent></Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {subStatus.sessions.map((session) => <button key={session.sessionId} type="button" onClick={() => setSelectedSession(session.sessionId)} className={`rounded-lg border p-4 text-left transition-colors ${selectedSession === session.sessionId ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:bg-muted/50"}`}>
                <div className="flex items-center justify-between"><span className="font-semibold">{session.sessionId === "SESSION_1" ? "Session 1 · Before Lunch" : "Session 2 · After Lunch"}</span><Badge variant={session.isSubmitted ? "default" : session.isOpen ? "outline" : "secondary"}>{session.isSubmitted ? "Submitted" : session.isOpen ? "Available" : "Not Available"}</Badge></div>
                <p className="mt-1 text-sm text-muted-foreground">{session.startTime} – {session.endTime}</p>
                {session.isSubmitted && <p className="mt-1 text-xs text-muted-foreground">Submitted by {session.submittedBy}{session.submittedAt ? ` at ${new Date(session.submittedAt).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}` : ""} · {session.absentCount} absent</p>}
              </button>)}
            </div>
          )}
          {selectedWindow && !selectedWindow.isOpen && !selectedWindow.isSubmitted && <p className="text-sm text-muted-foreground">{selectedSession === "SESSION_2" && subStatus?.sessions?.[0]?.isOpen ? "Session 2 opens after lunch." : `Attendance can be marked from ${selectedWindow.startTime} to ${selectedWindow.endTime} (Asia/Kolkata).`}</p>}
          {/* Already Submitted Warning Banner */}
          {isSubmittedToday && (
            <Card className="border-emerald-500/30 bg-emerald-50/70 dark:bg-emerald-950/30">
              <CardContent className="flex items-center gap-3 py-3.5">
                <div className="rounded-full bg-emerald-500/20 p-2 text-emerald-700 dark:text-emerald-300 shrink-0">
                  <CheckCircle2 className="size-5" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                    {selectedSession === "SESSION_1" ? "Session 1 Attendance Submitted" : "Session 2 Attendance Submitted"}
                  </p>
                  <p className="text-xs text-emerald-800 dark:text-emerald-300/80">
                    Attendance for {user?.year} Section {user?.section} was submitted by <strong>{selectedWindow?.submittedBy}</strong>
                    {selectedWindow?.submittedAt ? ` on ${new Date(selectedWindow.submittedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ""} ({selectedWindow?.absentCount ?? 0} absentees recorded).
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
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const todayStr = new Date().toISOString().split("T")[0];
                      const attCols = [
                        { key: "rollNumber", header: "Roll Number" },
                        { key: "name", header: "Student Name" },
                        { key: "year", header: "Academic Year", transform: (_: any, r: any) => r.year || user?.year || "" },
                        { key: "section", header: "Section", transform: (_: any, r: any) => r.section || user?.section || "" },
                        {
                          key: "status",
                          header: "Today's Status",
                          transform: (_: any, r: any) => absentRolls.has(r.rollNumber) ? "Absent" : "Present",
                        },
                        { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
                        { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
                      ];
                      exportToCSV(
                        filteredStudents,
                        `Attendance_${user?.year ? user.year.replace(/\s+/g, "_") : "Year"}_Section_${user?.section || "Sec"}_${todayStr}`,
                        attCols
                      );
                    }}
                    disabled={filteredStudents.length === 0}
                    className="gap-1.5"
                    title="Export today's attendance sheet to Excel/CSV"
                  >
                    <Download className="size-4" /> Export Sheet
                  </Button>
                  {!isSubmittedToday && (
                    <Button variant="outline" size="sm" onClick={markAllPresent}>
                      Mark All Present
                    </Button>
                  )}
                </div>
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
                  <ErrorState title="Failed to load students" description={error} retry={reload} />
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
                              <div className="flex items-center gap-2">
                                <Badge variant="destructive" className="gap-1">
                                  <UserX className="size-3" /> ABSENT
                                </Badge>
                                {isSubmittedToday && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="h-7 text-xs px-2 gap-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 border-emerald-300 dark:border-emerald-800"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setCorrectionTarget(s);
                                      setCorrectionReason("");
                                    }}
                                    title="Correct status to Present with mandatory reason"
                                  >
                                    <Edit3 className="size-3" /> Update
                                  </Button>
                                )}
                              </div>
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
                    disabled={submitting || !students || students.length === 0 || !isWindowOpen || !subStatus?.timetable?.configured}
                  >
                    <Send className="size-4 mr-2" />
                    {submitting ? "Submitting..." : `Submit ${selectedSession === "SESSION_1" ? "Session 1" : "Session 2"} Attendance`}
                  </Button>
                )}

                {isSubmittedToday && (
                  <p className="text-[11px] text-center text-muted-foreground">
                    This session is locked. Use <strong>Update</strong> next to an absent student to record a correction reason.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Attendance Correction Modal */}
          <Dialog open={!!correctionTarget} onOpenChange={(open) => !open && setCorrectionTarget(null)}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Edit3 className="size-5 text-emerald-600" />
                  Update Student Attendance
                </DialogTitle>
                <DialogDescription>
                  Correct an absent student to Present. A detailed mandatory reason is required for the audit trail.
                </DialogDescription>
              </DialogHeader>

              {correctionTarget && (
                <div className="space-y-4 pt-2">
                  <div className="rounded-lg bg-muted/60 p-3 text-xs space-y-1.5 border">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Student Name:</span>
                      <span className="font-bold text-foreground">{correctionTarget.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Roll Number:</span>
                      <span className="font-mono font-semibold text-foreground">{correctionTarget.rollNumber}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Academic Year & Section:</span>
                      <span>{user?.year} &bull; Section {user?.section}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t">
                      <span className="text-muted-foreground">Status Change:</span>
                      <span className="font-bold text-emerald-600 dark:text-emerald-400">ABSENT &rarr; PRESENT</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="correction-reason" className="text-xs font-semibold flex items-center justify-between">
                      <span>Reason for Attendance Correction *</span>
                      <span className="text-[10px] text-muted-foreground">(Mandatory, min 5 chars)</span>
                    </Label>
                    <textarea
                      id="correction-reason"
                      rows={3}
                      value={correctionReason}
                      onChange={(e) => setCorrectionReason(e.target.value)}
                      placeholder="e.g. Student arrived late with official permission from HOD, marked present after roll call."
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                    {correctionReason.trim().length > 0 && correctionReason.trim().length < 5 && (
                      <p className="text-[11px] text-rose-500">Reason must be at least 5 characters long.</p>
                    )}
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setCorrectionTarget(null)}
                      disabled={correcting}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={handleCorrectAttendance}
                      disabled={correcting || correctionReason.trim().length < 5}
                    >
                      {correcting ? "Saving Correction..." : "Confirm & Mark Present"}
                    </Button>
                  </div>
                </div>
              )}
            </DialogContent>
          </Dialog>
        </>
      )}
    </CRLRLayout>
  );
}

