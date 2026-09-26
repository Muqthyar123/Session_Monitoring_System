import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { CheckCircle2, UserX, Search, Send, GraduationCap, AlertTriangle } from "lucide-react";
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
  submitStudentAttendance,
} from "@/services/studentAttendanceService";
import type { StudentItem } from "@/services/studentService";

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
  const { data: students, loading, error, reload } = useAsyncData(() => getCRLRStudents(), []);

  const [search, setSearch] = useState("");
  // Set of rollNumbers marked as ABSENT
  const [absentRolls, setAbsentRolls] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

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
    setAbsentRolls(new Set());
  };

  const selectedAbsentees = useMemo(() => {
    if (!students) return [];
    return students.filter((s) => absentRolls.has(s.rollNumber));
  }, [students, absentRolls]);

  const handleSubmit = async () => {
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
      setAbsentRolls(new Set());
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to submit student attendance.");
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
                {user?.year} &bull; Section {user?.section} &bull; CR/LR: {user?.name}
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
              <CardTitle>Class Roll Call</CardTitle>
              <CardDescription>
                Check the box next to a student to mark them as ABSENT today.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={markAllPresent}>
              Mark All Present
            </Button>
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

            {loading ? (
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
                      className={`flex cursor-pointer items-center justify-between p-3.5 transition-colors ${
                        isAbsent ? "bg-rose-500/10 dark:bg-rose-950/20" : "hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox
                          checked={isAbsent}
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
              Review absent students before submitting daily record.
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

            <Button
              className="w-full"
              size="lg"
              onClick={handleSubmit}
              disabled={submitting || !students || students.length === 0}
            >
              <Send className="size-4 mr-2" />
              {submitting ? "Submitting..." : "Submit Attendance Record"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </CRLRLayout>
  );
}
