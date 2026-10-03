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
  Clock,
  UserCheck,
  Building2,
  FileSpreadsheet,
} from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getAbsenteeYears,
  getAbsenteeSections,
  getStudentAnalyticsSummary,
  getStudentCompleteHistory,
  type StudentAnalyticsSummaryItem,
  type AbsenteeStudentItem,
} from "@/services/studentAttendanceService";
import { getStudents, type StudentItem } from "@/services/studentService";

export const Route = createFileRoute("/admin/student-history")({
  head: () => ({
    meta: [
      { title: "Student Absence History — Admin Portal" },
      { name: "description", content: "Comprehensive hierarchy and detailed absence records with mentor audit notes across all academic years." },
    ],
  }),
  component: AdminStudentHistoryPage,
});

const DEFAULT_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];
const DEFAULT_SECTIONS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];

function AdminStudentHistoryPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [globalSearch, setGlobalSearch] = useState("");

  // Level 1: Dynamic Years
  const {
    data: dbYears,
    loading: loadingYears,
  } = useAsyncData(() => getAbsenteeYears().catch(() => DEFAULT_YEARS), []);

  const normalizedYears: { year: string; studentCount?: number; absenteeCount?: number }[] = useMemo(() => {
    if (!dbYears || !Array.isArray(dbYears)) {
      return DEFAULT_YEARS.map((y) => ({ year: y }));
    }
    return dbYears.map((item: any) => {
      if (typeof item === "string") return { year: item };
      return {
        year: item.year || "2nd Year",
        studentCount: item.studentCount,
        absenteeCount: item.absenteeCount,
      };
    });
  }, [dbYears]);

  // Level 2: Dynamic Sections for Selected Year
  const {
    data: dbSections,
    loading: loadingSections,
  } = useAsyncData(
    () => (selectedYear ? getAbsenteeSections(selectedYear).catch(() => DEFAULT_SECTIONS) : Promise.resolve([])),
    [selectedYear]
  );

  const normalizedSections: { section: string; studentCount?: number; absenteeCount?: number }[] = useMemo(() => {
    if (!dbSections || !Array.isArray(dbSections)) {
      return DEFAULT_SECTIONS.map((s) => ({ section: s }));
    }
    return dbSections.map((item: any) => {
      if (typeof item === "string") return { section: item };
      return {
        section: item.section || "A",
        studentCount: item.studentCount,
        absenteeCount: item.absenteeCount,
      };
    });
  }, [dbSections]);

  // Level 3: Students list for selected Year + Section
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

  // Global Search results when user searches across all students
  const {
    data: searchResults,
    loading: loadingGlobalSearch,
  } = useAsyncData(
    () =>
      globalSearch.trim().length >= 2
        ? getStudents(undefined, undefined, globalSearch.trim())
        : Promise.resolve([]),
    [globalSearch]
  );

  // Level 4: Complete Student History Modal
  const [activeStudent, setActiveStudent] = useState<{
    studentName: string;
    rollNumber: string;
    year: string;
    section: string;
    studentPhone?: string;
    parentPhone?: string;
    totalAbsences?: number;
    attendancePercentage?: number;
  } | null>(null);

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
    const term = globalSearch.trim().toLowerCase();
    if (!term) return summaryList;
    return summaryList.filter(
      (s) =>
        s.studentName.toLowerCase().includes(term) ||
        s.rollNumber.toLowerCase().includes(term)
    );
  }, [summaryList, globalSearch]);

  const isGlobalSearchActive = !selectedSection && globalSearch.trim().length >= 2;

  return (
    <AdminLayout>
      <PageHeader
        title="Student Absence History & Records"
        description="Dynamic academic drill-down: Year → Section → Students → Full Absences with Mentor remarks and timestamp."
        actions={
          <div className="flex items-center gap-2">
            {selectedSection ? (
              <Button variant="outline" size="sm" onClick={() => setSelectedSection(null)}>
                <ArrowLeft className="size-4 mr-2" /> Back to Sections
              </Button>
            ) : selectedYear ? (
              <Button variant="outline" size="sm" onClick={() => setSelectedYear(null)}>
                <ArrowLeft className="size-4 mr-2" /> Back to Years
              </Button>
            ) : null}
          </div>
        }
      />

      {/* Global Search Bar */}
      <div className="relative max-w-lg">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Global student search by name or roll number..."
          value={globalSearch}
          onChange={(e) => setGlobalSearch(e.target.value)}
          className="pl-9 bg-card"
        />
        {globalSearch && (
          <button
            onClick={() => setGlobalSearch("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground"
          >
            Clear
          </button>
        )}
      </div>

      {/* GLOBAL SEARCH ACTIVE VIEW */}
      {isGlobalSearchActive && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Global Search Results for &ldquo;{globalSearch}&rdquo;
            </h2>
            <span className="text-xs text-muted-foreground">
              {searchResults?.length || 0} student(s) found
            </span>
          </div>

          {loadingGlobalSearch ? (
            <LoadingState label="Searching all students across database..." />
          ) : !searchResults || searchResults.length === 0 ? (
            <EmptyState
              title="No students found"
              description={`No student matched the search "${globalSearch}".`}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {searchResults.map((s) => (
                <Card key={s.id} className="flex flex-col justify-between hover:border-primary/50 transition-colors">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-base font-bold">{s.name}</CardTitle>
                        <p className="font-mono text-xs text-muted-foreground">{s.rollNumber}</p>
                      </div>
                      <Badge variant="outline">
                        {s.year || "2nd Year"} &bull; {s.section}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-2 space-y-3">
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>Branch: <strong className="text-foreground">{s.branch || "CSE"}</strong></div>
                      {s.crlrName && <div>CR/LR: <strong className="text-foreground">{s.crlrName}</strong></div>}
                    </div>
                    <Button
                      variant="default"
                      size="sm"
                      className="w-full"
                      onClick={() =>
                        setActiveStudent({
                          studentName: s.name,
                          rollNumber: s.rollNumber,
                          year: s.year || "2nd Year",
                          section: s.section,
                          studentPhone: s.studentPhone || undefined,
                          parentPhone: s.parentPhone || undefined,
                        })
                      }
                    >
                      <History className="size-3.5 mr-2" /> View Absence History
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 1: Select Academic Year (when not in global search) */}
      {!isGlobalSearchActive && !selectedYear && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">Step 1: Select Academic Year</h2>
            <span className="text-xs text-muted-foreground">Select a year to explore sections</span>
          </div>

          {loadingYears ? (
            <LoadingState label="Loading academic years..." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {normalizedYears.map((item) => (
                <Card
                  key={item.year}
                  onClick={() => setSelectedYear(item.year)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group bg-card"
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-base font-bold">{item.year}</CardTitle>
                    <GraduationCap className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </CardHeader>
                  <CardContent className="pt-2">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      {item.studentCount !== undefined ? (
                        <span>{item.studentCount} Students</span>
                      ) : (
                        <span>Explore sections</span>
                      )}
                      {item.absenteeCount !== undefined && item.absenteeCount > 0 ? (
                        <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                          {item.absenteeCount} Absent Today
                        </Badge>
                      ) : null}
                    </div>
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

      {/* LEVEL 2: Select Section */}
      {!isGlobalSearchActive && selectedYear && !selectedSection && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-sm px-3 py-1 bg-primary/10 text-primary border-primary/20">
              {selectedYear}
            </Badge>
            <span className="text-sm text-muted-foreground">Step 2: Select Section</span>
          </div>

          {loadingSections ? (
            <LoadingState label="Loading sections for academic year..." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {normalizedSections.map((item) => (
                <Card
                  key={item.section}
                  onClick={() => setSelectedSection(item.section)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group bg-card"
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg font-bold">Section {item.section}</CardTitle>
                      <Building2 className="size-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                    <CardDescription>{selectedYear} Roster &amp; History</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {item.studentCount !== undefined && (
                      <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                        <span>{item.studentCount} Students</span>
                        {item.absenteeCount !== undefined && item.absenteeCount > 0 && (
                          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                            {item.absenteeCount} Absent Today
                          </Badge>
                        )}
                      </div>
                    )}
                    <div className="flex items-center justify-end text-xs font-semibold text-primary mt-2">
                      View Students <ChevronRight className="size-4 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 3: Student Roster Cards for Selected Year & Section */}
      {!isGlobalSearchActive && selectedYear && selectedSection && (
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
            <span className="text-xs text-muted-foreground">
              {filteredSummary.length} student(s) in this section
            </span>
          </div>

          {loadingSummary ? (
            <LoadingState label="Loading student attendance roster..." />
          ) : errorSummary ? (
            <ErrorState title="Failed to load roster" description={errorSummary.message} retry={reloadSummary} />
          ) : !summaryList || summaryList.length === 0 ? (
            <EmptyState
              title="No student records found"
              description={`No students are currently registered under ${selectedYear} Section ${selectedSection}.`}
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
                  <Card key={st.rollNumber} className="flex flex-col justify-between hover:shadow-xs transition-shadow">
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
                        onClick={() =>
                          setActiveStudent({
                            studentName: st.studentName,
                            rollNumber: st.rollNumber,
                            year: st.year,
                            section: st.section,
                            studentPhone: st.studentPhone || undefined,
                            parentPhone: st.parentPhone || undefined,
                            totalAbsences: st.totalAbsences,
                            attendancePercentage: st.attendancePercentage,
                          })
                        }
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
        <DialogContent className="sm:max-w-xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="size-5 text-primary" />
              <span>Student Attendance History: {activeStudent?.studentName}</span>
            </DialogTitle>
            <DialogDescription>
              Roll Number: <span className="font-mono font-semibold text-foreground">{activeStudent?.rollNumber}</span> &bull; {activeStudent?.year} ({activeStudent?.section})
            </DialogDescription>
          </DialogHeader>

          {activeStudent && (
            <div className="space-y-4 py-2">
              {/* Phone Action Dialers */}
              <div className="grid grid-cols-2 gap-3">
                {activeStudent.studentPhone ? (
                  <a
                    href={`tel:${activeStudent.studentPhone}`}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors shadow-xs"
                  >
                    <Phone className="size-3.5" /> Call Student ({activeStudent.studentPhone})
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Student Phone
                  </Button>
                )}

                {activeStudent.parentPhone ? (
                  <a
                    href={`tel:${activeStudent.parentPhone}`}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors shadow-xs"
                  >
                    <PhoneCall className="size-3.5" /> Call Parent ({activeStudent.parentPhone})
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Parent Phone
                  </Button>
                )}
              </div>

              {/* History list */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                    <Clock className="size-3.5" /> Absence Records (Sorted Newest First):
                  </h4>
                  {historyList && (
                    <span className="text-xs font-medium text-muted-foreground">
                      {historyList.length} absence(s)
                    </span>
                  )}
                </div>

                {loadingHistory ? (
                  <LoadingState label="Loading complete absence logs..." />
                ) : errorHistory ? (
                  <ErrorState title="Failed to load history" description={errorHistory.message} />
                ) : !historyList || historyList.length === 0 ? (
                  <div className="rounded-md bg-emerald-500/10 p-4 text-center text-xs text-emerald-700 dark:text-emerald-400">
                    <CheckCircle2 className="size-5 mx-auto mb-1 text-emerald-600" />
                    No recorded absences found. Student has 100% attendance!
                  </div>
                ) : (
                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {historyList.map((log) => (
                      <div
                        key={log.id}
                        className="rounded-lg border p-3.5 text-xs space-y-2 bg-card shadow-xs"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1 font-semibold text-rose-600 bg-rose-50 dark:bg-rose-950/30 px-2 py-0.5 rounded">
                              <UserX className="size-3.5" /> Absent on {log.date}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {log.session || "Academic Session"}
                            </Badge>
                          </div>
                          {log.submittedBy && (
                            <span className="text-[11px] text-muted-foreground">
                              Submitted by: <span className="font-medium text-foreground">{log.submittedBy}</span>
                            </span>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-2 text-muted-foreground text-[11px]">
                          <div>
                            <span className="font-medium text-foreground">Subject: </span>
                            {log.subject || "Academic Class"}
                          </div>
                          <div>
                            <span className="font-medium text-foreground">Faculty: </span>
                            {log.faculty || "Assigned Faculty"}
                          </div>
                        </div>

                        <div className="rounded-md bg-muted/50 p-2.5 text-xs">
                          {log.reason ? (
                            <div className="space-y-1">
                              <p className="text-foreground">
                                <strong className="text-primary font-semibold">Absence Reason:</strong> {log.reason}
                              </p>
                              <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground pt-1.5 border-t border-muted">
                                <span className="flex items-center gap-1">
                                  <UserCheck className="size-3 text-primary" />
                                  Updated by Mentor: <strong className="text-foreground">{log.reasonUpdatedBy || "Assigned Mentor"}</strong>
                                </span>
                                {log.updatedAt && (
                                  <span>
                                    {new Date(log.updatedAt).toLocaleString("en-IN", {
                                      dateStyle: "medium",
                                      timeStyle: "short",
                                    })}
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : (
                            <p className="text-muted-foreground italic text-center py-0.5">
                              No reason recorded by mentor yet.
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
