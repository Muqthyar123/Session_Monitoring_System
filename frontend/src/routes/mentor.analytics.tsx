import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Search,
  ArrowLeft,
  ChevronRight,
  GraduationCap,
  Calendar,
  Phone,
  PhoneCall,
  History,
  CheckCircle2,
  AlertTriangle,
  UserX,
} from "lucide-react";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getMentorStudentsYears,
  getMentorStudentsSections,
} from "@/services/mentorService";
import {
  getStudentAnalyticsSummary,
  getStudentCompleteHistory,
  type StudentAnalyticsSummaryItem,
  type AbsenteeStudentItem,
} from "@/services/studentAttendanceService";

export const Route = createFileRoute("/mentor/analytics")({
  head: () => ({
    meta: [
      { title: "Student Attendance History — Mentor Portal" },
      { name: "description", content: "Inspect section student attendance rates and view full history logs." },
    ],
  }),
  component: MentorAttendanceHistoryPage,
});

function MentorAttendanceHistoryPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // LEVEL 1: Fetch dynamic years assigned to mentor
  const {
    data: yearCards,
    loading: loadingYears,
    error: errorYears,
    reload: reloadYears,
  } = useAsyncData(() => getMentorStudentsYears(), []);

  // LEVEL 2: Fetch dynamic sections for the selected year
  const {
    data: sectionCards,
    loading: loadingSections,
    error: errorSections,
    reload: reloadSections,
  } = useAsyncData(
    () => (selectedYear ? getMentorStudentsSections(selectedYear) : Promise.resolve([])),
    [selectedYear]
  );

  // LEVEL 3: Fetch summary when year & section selected
  const {
    data: summaryList,
    loading: loadingSummary,
    error: errorSummary,
    reload: reloadSummary,
  } = useAsyncData(
    () =>
      selectedYear && selectedSection
        ? getStudentAnalyticsSummary(selectedYear, selectedSection)
        : Promise.resolve([]),
    [selectedYear, selectedSection]
  );

  // Selected student for complete history modal
  const [activeStudent, setActiveStudent] = useState<StudentAnalyticsSummaryItem | null>(null);
  const [calledActive, setCalledActive] = useState<{ student?: boolean; parent?: boolean }>({});
  const {
    data: historyList,
    loading: loadingHistory,
    error: errorHistory,
  } = useAsyncData(
    () =>
      activeStudent ? getStudentCompleteHistory(activeStudent.rollNumber) : Promise.resolve([]),
    [activeStudent]
  );

  const filteredSummary = useMemo(() => {
    if (!summaryList) return [];
    const term = search.trim().toLowerCase();
    if (!term) return summaryList;
    return summaryList.filter(
      (s) =>
        s.studentName.toLowerCase().includes(term) ||
        s.rollNumber.toLowerCase().includes(term)
    );
  }, [summaryList, search]);

  return (
    <MentorLayout>
      <PageHeader
        title="Student Attendance History"
        description="Select Year and Section to inspect attendance percentages, absentee frequency, and complete historical records."
        actions={
          selectedSection ? (
            <Button variant="outline" size="sm" onClick={() => setSelectedSection(null)}>
              <ArrowLeft className="size-4 mr-2" /> Back to Sections
            </Button>
          ) : selectedYear ? (
            <Button variant="outline" size="sm" onClick={() => setSelectedYear(null)}>
              <ArrowLeft className="size-4 mr-2" /> Back to Years
            </Button>
          ) : undefined
        }
      />

      {/* LEVEL 1: Dynamic Academic Year Cards */}
      {!selectedYear && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">Select Academic Year</h2>
            <span className="text-xs text-muted-foreground">Click a year to view assigned sections</span>
          </div>

          {loadingYears ? (
            <LoadingState label="Loading academic years..." />
          ) : errorYears ? (
            <ErrorState title="Failed to load years" description={errorYears.message} retry={reloadYears} />
          ) : !yearCards || yearCards.length === 0 ? (
            <EmptyState
              title="No academic years found"
              description="No students or classes are assigned under your mentor scope."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {yearCards.map((yc) => (
                <Card
                  key={yc.year}
                  onClick={() => setSelectedYear(yc.year)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-base font-bold">{yc.year}</CardTitle>
                    <GraduationCap className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </CardHeader>
                  <CardContent className="pt-2">
                    <p className="text-xs text-muted-foreground">Enrolled: {yc.studentCount} Students</p>
                    <div className="mt-4 flex items-center justify-end text-xs font-semibold text-primary">
                      View Sections <ChevronRight className="size-4 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 2: Dynamic Sections for Selected Year */}
      {selectedYear && !selectedSection && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm px-3 py-1 font-semibold">
                {selectedYear}
              </Badge>
              <span className="text-sm text-muted-foreground">Select Section</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setSelectedYear(null)}>
              <ArrowLeft className="size-4 mr-1" /> All Years
            </Button>
          </div>

          {loadingSections ? (
            <LoadingState label={`Loading sections for ${selectedYear}...`} />
          ) : errorSections ? (
            <ErrorState title="Failed to load sections" description={errorSections.message} retry={reloadSections} />
          ) : !sectionCards || sectionCards.length === 0 ? (
            <EmptyState
              title="No sections found"
              description={`No sections configured for ${selectedYear}.`}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {sectionCards.map((sc) => (
                <Card
                  key={sc.section}
                  onClick={() => setSelectedSection(sc.section)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-bold">{selectedYear} &bull; Section {sc.section}</CardTitle>
                    <CardDescription>{sc.studentCount} Students Enrolled</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-end text-xs font-semibold text-primary mt-2">
                      Attendance History <ChevronRight className="size-4 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 3: Student Summary Table for Selected Year & Section */}
      {selectedYear && selectedSection && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-sm font-semibold">
                {selectedYear}
              </Badge>
              <Badge variant="default" className="text-sm font-semibold">
                Section {selectedSection}
              </Badge>
            </div>

            <div className="relative max-w-xs flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search student or roll number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          {loadingSummary ? (
            <LoadingState label="Loading student analytics..." />
          ) : errorSummary ? (
            <ErrorState title="Failed to load summary" description={errorSummary.message} retry={reloadSummary} />
          ) : !summaryList || summaryList.length === 0 ? (
            <EmptyState
              title="No student records found"
              description={`No students enrolled or recorded for ${selectedYear} Section ${selectedSection}.`}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredSummary.map((st) => {
                const pct = st.attendancePercentage;
                const statusBadge =
                  pct >= 85 ? (
                    <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 bg-emerald-50 dark:bg-emerald-950/20">
                      {pct}% Attendance
                    </Badge>
                  ) : pct >= 75 ? (
                    <Badge variant="outline" className="border-amber-500/40 text-amber-600 bg-amber-50 dark:bg-amber-950/20">
                      {pct}% Attendance
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      {pct}% (Low)
                    </Badge>
                  );

                return (
                  <Card key={st.rollNumber} className="flex flex-col justify-between">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-base font-bold">{st.studentName}</CardTitle>
                          <p className="font-mono text-xs text-muted-foreground">{st.rollNumber}</p>
                        </div>
                        {statusBadge}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between text-xs text-muted-foreground border-t pt-2">
                        <span>Total Absences: <strong className="text-foreground">{st.totalAbsences} days</strong></span>
                        <span>Tracked Days: <strong className="text-foreground">{st.totalDays}</strong></span>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => {
                          setActiveStudent(st);
                          setCalledActive({});
                        }}
                      >
                        <History className="size-3.5 mr-2" /> Complete History
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 4: Complete Student History Modal */}
      <Dialog open={!!activeStudent} onOpenChange={(open) => !open && setActiveStudent(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="size-5 text-primary" />
              <span>Attendance History: {activeStudent?.studentName}</span>
            </DialogTitle>
            <DialogDescription>
              Roll Number: <span className="font-mono font-semibold">{activeStudent?.rollNumber}</span> &bull; {activeStudent?.year} ({activeStudent?.section})
            </DialogDescription>
          </DialogHeader>

          {activeStudent && (
            <div className="space-y-4 py-2">
              {/* Phone Action Dialers */}
              <div className="grid grid-cols-2 gap-3">
                {activeStudent.studentPhone ? (
                  <a
                    href={`tel:${activeStudent.studentPhone}`}
                    onClick={() => setCalledActive((prev) => ({ ...prev, student: true }))}
                    className={cn(
                      "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-colors duration-200",
                      calledActive.student
                        ? "bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 hover:bg-emerald-900/90 shadow-inner"
                        : "bg-emerald-600 text-white hover:bg-emerald-700"
                    )}
                    title={`Call Student (${activeStudent.studentPhone})`}
                  >
                    {calledActive.student ? (
                      <>
                        <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0" /> Called Student
                      </>
                    ) : (
                      <>
                        <Phone className="size-3.5 shrink-0" /> Call Student
                      </>
                    )}
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Student Phone
                  </Button>
                )}

                {activeStudent.parentPhone ? (
                  <a
                    href={`tel:${activeStudent.parentPhone}`}
                    onClick={() => setCalledActive((prev) => ({ ...prev, parent: true }))}
                    className={cn(
                      "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-colors duration-200",
                      calledActive.parent
                        ? "bg-blue-950/80 text-blue-300 border border-blue-500/50 hover:bg-blue-900/90 shadow-inner"
                        : "bg-blue-600 text-white hover:bg-blue-700"
                    )}
                    title={`Call Parent (${activeStudent.parentPhone})`}
                  >
                    {calledActive.parent ? (
                      <>
                        <CheckCircle2 className="size-3.5 text-blue-400 shrink-0" /> Called Parent
                      </>
                    ) : (
                      <>
                        <PhoneCall className="size-3.5 shrink-0" /> Call Parent
                      </>
                    )}
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Parent Phone
                  </Button>
                )}
              </div>

              {/* History list */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                  Absence Log (Sorted Newest First):
                </h4>

                {loadingHistory ? (
                  <LoadingState label="Loading complete history..." />
                ) : errorHistory ? (
                  <ErrorState title="Failed to load history" description={errorHistory.message} />
                ) : !historyList || historyList.length === 0 ? (
                  <div className="rounded-md bg-emerald-500/10 p-4 text-center text-xs text-emerald-700 dark:text-emerald-400">
                    No recorded absences found. Student has 100% attendance!
                  </div>
                ) : (
                  <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                    {historyList.map((log) => (
                      <div
                        key={log.id}
                        className="rounded-md border p-3 text-xs space-y-1 bg-muted/30"
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span className="flex items-center gap-1.5 text-rose-600">
                            <UserX className="size-3.5" /> Absent on {log.date}
                          </span>
                          {log.submittedBy && (
                            <span className="text-muted-foreground font-normal">
                              Submitted by: {log.submittedBy}
                            </span>
                          )}
                        </div>
                        {log.reason ? (
                          <p className="text-foreground pt-1">
                            <strong>Mentor Note:</strong> {log.reason}
                          </p>
                        ) : (
                          <p className="text-muted-foreground italic pt-1">No reason recorded by mentor yet.</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </MentorLayout>
  );
}
