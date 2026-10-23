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
  UserCheck,
  Building2,
  Download,
} from "lucide-react";
import { exportToCSV } from "@/utils/exportUtils";
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

export const Route = createFileRoute("/admin/student-analytics")({
  head: () => ({
    meta: [
      { title: "Student Attendance Analytics — Admin Portal" },
      { name: "description", content: "Comprehensive overview of dynamic student attendance metrics across all academic years and sections." },
    ],
  }),
  component: AdminStudentAnalyticsPage,
});

const DEFAULT_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];
const DEFAULT_SECTIONS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"];

function AdminStudentAnalyticsPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [globalSearch, setGlobalSearch] = useState("");

  // Level 1: Dynamic Years
  const {
    data: dbYears,
    loading: loadingYears,
    error: errorYears,
    reload: reloadYears,
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
    error: errorSections,
    reload: reloadSections,
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

  // Global Search results when searching across all students
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

  // Selected student for complete history modal
  const [activeStudent, setActiveStudent] = useState<StudentAnalyticsSummaryItem | null>(null);
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

  const isGlobalSearchActive = !selectedSection && globalSearch.trim().length >= 2;

  return (
    <AdminLayout>
      <PageHeader
        title="Student Attendance Analytics"
        description="Comprehensive real-time student attendance metrics, dynamic section drill-down, and absence records across academic years."
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
      {!selectedSection && (
        <div className="relative max-w-lg mb-6">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search any student across the college by name or roll number..."
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
      )}

      {/* GLOBAL SEARCH RESULTS VIEW */}
      {isGlobalSearchActive && (
        <div className="space-y-4 mb-8">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Global Search Results for &ldquo;{globalSearch}&rdquo;
            </h2>
            <span className="text-xs text-muted-foreground">
              {searchResults?.length || 0} student(s) found
            </span>
          </div>

          {loadingGlobalSearch ? (
            <LoadingState label="Searching student directory..." />
          ) : !searchResults || searchResults.length === 0 ? (
            <EmptyState
              title="No students matched search"
              description={`Could not find any student matching "${globalSearch}".`}
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {searchResults.map((st) => (
                <Card
                  key={st.rollNumber}
                  className="hover:border-primary transition-all cursor-pointer"
                  onClick={() => {
                    setActiveStudent({
                      studentName: st.name,
                      rollNumber: st.rollNumber,
                      year: st.year || selectedYear || "2nd Year",
                      section: st.section || "A",
                      studentPhone: st.studentPhone,
                      parentPhone: st.parentPhone,
                      totalAbsences: 0,
                      totalDays: 0,
                      attendancePercentage: 100,
                    });
                  }}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-sm font-bold">{st.name}</CardTitle>
                        <p className="font-mono text-xs text-muted-foreground">{st.rollNumber}</p>
                      </div>
                      <Badge variant="outline">{st.section}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs">
                    <div className="flex justify-between text-muted-foreground">
                      <span>{st.year || "2nd Year"}</span>
                      <span>{st.branch || "CSE"}</span>
                    </div>
                    <Button variant="outline" size="sm" className="w-full text-xs h-7 mt-2">
                      <History className="size-3 mr-1.5" /> View Absence History
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 1: Dynamic Academic Years */}
      {!selectedYear && !isGlobalSearchActive && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">Select Academic Year</h2>
            <span className="text-xs text-muted-foreground">
              {normalizedYears.length} Academic Years Active
            </span>
          </div>

          {loadingYears ? (
            <LoadingState label="Loading academic years..." />
          ) : errorYears ? (
            <ErrorState title="Failed to load years" description={errorYears.message} retry={reloadYears} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {normalizedYears.map((item) => (
                <Card
                  key={item.year}
                  onClick={() => setSelectedYear(item.year)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-base font-bold">{item.year}</CardTitle>
                    <GraduationCap className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </CardHeader>
                  <CardContent className="pt-2 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Total Enrolled:</span>
                      <strong className="text-foreground">{item.studentCount ?? "Registered"} Students</strong>
                    </div>
                    {item.absenteeCount !== undefined && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Today's Absences:</span>
                        <Badge variant={item.absenteeCount > 0 ? "destructive" : "outline"} className="text-[10px]">
                          {item.absenteeCount} absent
                        </Badge>
                      </div>
                    )}
                    <div className="flex items-center justify-end text-xs font-semibold text-primary pt-2 border-t">
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
      {selectedYear && !selectedSection && !isGlobalSearchActive && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm px-3 py-1 font-semibold">
                {selectedYear}
              </Badge>
              <span className="text-sm text-muted-foreground">Choose Section</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {normalizedSections.length} Sections Available
            </span>
          </div>

          {loadingSections ? (
            <LoadingState label={`Loading sections for ${selectedYear}...`} />
          ) : errorSections ? (
            <ErrorState title="Failed to load sections" description={errorSections.message} retry={reloadSections} />
          ) : normalizedSections.length === 0 ? (
            <EmptyState
              title="No Sections Found"
              description={`No sections are currently mapped for ${selectedYear}.`}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {normalizedSections.map((sec) => (
                <Card
                  key={sec.section}
                  onClick={() => setSelectedSection(sec.section)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                    <div>
                      <CardTitle className="text-lg font-bold">Section {sec.section}</CardTitle>
                      <CardDescription>{selectedYear}</CardDescription>
                    </div>
                    <Building2 className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </CardHeader>
                  <CardContent className="pt-2 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Students:</span>
                      <strong className="text-foreground">{sec.studentCount ?? "Registered"}</strong>
                    </div>
                    {sec.absenteeCount !== undefined && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Today's Absences:</span>
                        <Badge variant={sec.absenteeCount > 0 ? "destructive" : "outline"} className="text-[10px]">
                          {sec.absenteeCount} absent
                        </Badge>
                      </div>
                    )}
                    <div className="flex items-center justify-end text-xs font-semibold text-primary pt-2 border-t">
                      Student Analytics <ChevronRight className="size-4 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 3: Student Summary Cards for Selected Year & Section */}
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
              <span className="text-xs text-muted-foreground ml-2">
                {filteredSummary.length} student(s) tracked
              </span>
            </div>

            <div className="flex items-center gap-3 flex-1 justify-end">
              <div className="relative max-w-xs w-full">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Filter student or roll number..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 bg-card"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const cols = [
                    { key: "rollNumber", header: "Roll Number" },
                    { key: "studentName", header: "Student Name" },
                    { key: "year", header: "Academic Year" },
                    { key: "section", header: "Section" },
                    { key: "attendancePercentage", header: "Attendance %" },
                    { key: "totalAbsences", header: "Total Absences" },
                    { key: "totalDays", header: "Total Days Tracked" },
                    { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
                    { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
                  ];
                  exportToCSV(
                    filteredSummary,
                    `Student_Analytics_${selectedYear.replace(/\s+/g, "_")}_Section_${selectedSection}`,
                    cols
                  );
                }}
                disabled={filteredSummary.length === 0}
                className="gap-1.5 bg-emerald-600/10 text-emerald-600 hover:bg-emerald-600/20 border-emerald-500/30"
                title="Export student analytics to Excel/CSV"
              >
                <Download className="size-4" /> Export Analytics
              </Button>
            </div>
          </div>

          {loadingSummary ? (
            <LoadingState label="Calculating realtime student attendance analytics..." />
          ) : errorSummary ? (
            <ErrorState title="Failed to load summary" description={errorSummary.message} retry={reloadSummary} />
          ) : !summaryList || summaryList.length === 0 ? (
            <EmptyState
              title="No student records found"
              description={`No students registered for ${selectedYear} Section ${selectedSection}.`}
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
                  <Card key={st.rollNumber} className="flex flex-col justify-between hover:shadow-sm transition-shadow">
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
                        className="w-full text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                        onClick={() => setActiveStudent(st)}
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
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors"
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
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
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
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                    Absence Log (Sorted Newest First):
                  </h4>
                  {historyList && historyList.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const cols = [
                          { key: "date", header: "Date" },
                          { key: "rollNumber", header: "Roll Number" },
                          { key: "studentName", header: "Student Name" },
                          { key: "year", header: "Academic Year" },
                          { key: "section", header: "Section" },
                          { key: "status", header: "Status" },
                          { key: "reason", header: "Reason / Remark", transform: (v: any) => v || "" },
                          { key: "submittedBy", header: "Submitted By", transform: (v: any) => v || "" },
                        ];
                        exportToCSV(historyList, `Student_Absence_Log_${activeStudent?.rollNumber}`, cols);
                      }}
                      className="h-7 text-xs gap-1"
                      title="Export student absence log to CSV"
                    >
                      <Download className="size-3.5" /> Export Log
                    </Button>
                  )}
                </div>

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
                        className="rounded-lg border p-3.5 text-xs space-y-2 bg-card shadow-xs"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
                          <div className="flex items-center gap-2">
                            <span className="inline-flex items-center gap-1 font-semibold text-rose-600 bg-rose-50 dark:bg-rose-950/30 px-2 py-0.5 rounded">
                              <UserX className="size-3.5" /> Absent on {log.date}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {log.session || "Session"}
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

                        <div className="rounded-md bg-muted/50 p-2 text-xs">
                          {log.reason ? (
                            <div className="space-y-1">
                              <p className="text-foreground">
                                <strong className="text-primary font-semibold">Absence Reason:</strong> {log.reason}
                              </p>
                              <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-muted">
                                <span>
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
