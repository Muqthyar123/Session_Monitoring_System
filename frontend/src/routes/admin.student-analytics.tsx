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
  Building2,
  Download,
  Lock,
  Save,
  CalendarClock,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
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
  getAbsenteeStudents,
  saveAbsenceReason,
  getStudentCompleteHistory,
  type AbsenteeStudentItem,
} from "@/services/studentAttendanceService";
import { createPlannedAbsence } from "@/services/plannedAbsenceService";
import { getStudents, type StudentItem } from "@/services/studentService";

export const Route = createFileRoute("/admin/student-analytics")({
  head: () => ({
    meta: [
      { title: "Student Absentees — Admin Portal" },
      { name: "description", content: "Inspect today's absentee students across academic years and sections, track dialer calls, and inspect recorded mentor notes." },
    ],
  }),
  component: AdminStudentAbsenteesPage,
});


function AdminStudentAbsenteesPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(() => {
    return sessionStorage.getItem("admin_sa_year") || null;
  });
  const [selectedSection, setSelectedSection] = useState<string | null>(() => {
    return sessionStorage.getItem("admin_sa_section") || null;
  });
  const [sectionSearch, setSectionSearch] = useState("");
  const [globalSearch, setGlobalSearch] = useState("");

  const handleSelectYear = (yr: string | null) => {
    setSelectedYear(yr);
    if (yr) {
      sessionStorage.setItem("admin_sa_year", yr);
    } else {
      sessionStorage.removeItem("admin_sa_year");
      sessionStorage.removeItem("admin_sa_section");
      setSelectedSection(null);
    }
  };

  const handleSelectSection = (sec: string | null) => {
    setSelectedSection(sec);
    if (sec) {
      sessionStorage.setItem("admin_sa_section", sec);
    } else {
      sessionStorage.removeItem("admin_sa_section");
    }
  };

  // Level 1: Dynamic Years with student and absentee counts
  const {
    data: dbYears,
    loading: loadingYears,
    error: errorYears,
    reload: reloadYears,
  } = useAsyncData(() => getAbsenteeYears(), []);

  const normalizedYears: { year: string; studentCount?: number; absenteeCount?: number; unassignedStudentCount?: number }[] = useMemo(() => {
    if (!dbYears || !Array.isArray(dbYears)) {
      return [];
    }
    return dbYears.map((item) => {
      if (typeof item === "string") return { year: item };
      return {
        year: item.year || "2nd Year",
        ...(item.studentCount !== undefined ? { studentCount: item.studentCount } : {}),
        ...(item.absenteeCount !== undefined ? { absenteeCount: item.absenteeCount } : {}),
        ...(item.unassignedStudentCount !== undefined
          ? { unassignedStudentCount: item.unassignedStudentCount }
          : {}),
      };
    });
  }, [dbYears]);

  // Level 2: Dynamic Sections for Selected Year (Strict assigned sections only, deduplicated)
  const {
    data: dbSections,
    loading: loadingSections,
    error: errorSections,
    reload: reloadSections,
  } = useAsyncData(
    () => (selectedYear ? getAbsenteeSections(selectedYear) : Promise.resolve([])),
    [selectedYear]
  );

  const normalizedSections: { section: string; studentCount?: number; absenteeCount?: number }[] = useMemo(() => {
    if (!dbSections || !Array.isArray(dbSections) || dbSections.length === 0) {
      return [];
    }
    const seen = new Set<string>();
    const list: { section: string; studentCount?: number; absenteeCount?: number }[] = [];
    for (const item of dbSections) {
      const rawSec = typeof item === "string" ? item : (item.section || "");
      const cleanSec = rawSec.trim();
      const key = cleanSec.toUpperCase();
      if (cleanSec && !seen.has(key)) {
        seen.add(key);
        list.push({
          section: cleanSec,
          ...(typeof item !== "string" && item.studentCount !== undefined
            ? { studentCount: item.studentCount }
            : {}),
          ...(typeof item !== "string" && item.absenteeCount !== undefined
            ? { absenteeCount: item.absenteeCount }
            : {}),
        });
      }
    }
    return list;
  }, [dbSections]);

  // Level 3: Today's Marked Absentees for selected Year + Section
  const {
    data: absenteesList,
    loading: loadingAbsentees,
    error: errorAbsentees,
    reload: reloadAbsentees,
  } = useAsyncData(
    () =>
      selectedYear && selectedSection
        ? getAbsenteeStudents(selectedYear, selectedSection)
        : Promise.resolve([]),
    [selectedYear, selectedSection]
  );

  // Global student search results when searching across the institution
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

  // Level 4: Complete History modal for a student
  const [activeHistoryStudent, setActiveHistoryStudent] = useState<AbsenteeStudentItem | null>(null);
  const {
    data: historyRecords,
    loading: loadingHistory,
  } = useAsyncData(
    () =>
      activeHistoryStudent ? getStudentCompleteHistory(activeHistoryStudent.rollNumber) : Promise.resolve([]),
    [activeHistoryStudent]
  );

  // Today date string (YYYY-MM-DD)
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Absence comment and planned mode states
  const [absenceModes, setAbsenceModes] = useState<Record<string, "NORMAL" | "PLANNED">>({});
  const [dateRanges, setDateRanges] = useState<Record<string, { from: string; to: string }>>({});
  const [reasonInputs, setReasonInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  // Permanently locked reasons map for instant dynamic UI updates without reload
  const [lockedReasonMap, setLockedReasonMap] = useState<Record<string, { reason: string; updatedBy?: string }>>({});

  // Dialer call tracker for smooth color/badge toggle
  const [calledMap, setCalledMap] = useState<Record<string, { student?: boolean; parent?: boolean }>>({});

  const handleCallToggle = (recordId: string, type: "student" | "parent") => {
    setCalledMap((prev) => ({
      ...prev,
      [recordId]: {
        ...prev[recordId],
        [type]: !prev[recordId]?.[type],
      },
    }));
  };

  const handleModeChange = (id: string, mode: "NORMAL" | "PLANNED") => {
    setAbsenceModes((prev) => ({ ...prev, [id]: mode }));
    if (!dateRanges[id]) {
      setDateRanges((prev) => ({ ...prev, [id]: { from: todayStr, to: todayStr } }));
    }
  };

  const handleDateChange = (id: string, field: "from" | "to", val: string) => {
    setDateRanges((prev) => ({
      ...prev,
      [id]: {
        from: field === "from" ? val : (prev[id]?.from ?? todayStr),
        to: field === "to" ? val : (prev[id]?.to ?? todayStr),
      },
    }));
  };

  const handleReasonChange = (id: string, value: string) => {
    setReasonInputs((prev) => ({ ...prev, [id]: value }));
  };

  const handleSaveNormalReason = async (record: AbsenteeStudentItem) => {
    const recordId = record.id || record._id || record.rollNumber;
    const reasonText = reasonInputs[recordId] ?? record.reason ?? "";
    if (!reasonText.trim()) {
      toast.error("Please enter a reason or note before saving.");
      return;
    }

    setSavingId(recordId);
    try {
      await saveAbsenceReason(recordId, reasonText.trim());
      record.reason = reasonText.trim();
      record.reasonUpdatedBy = "Admin";
      setLockedReasonMap((prev) => ({
        ...prev,
        [recordId]: { reason: reasonText.trim(), updatedBy: "Admin" },
        [record.rollNumber]: { reason: reasonText.trim(), updatedBy: "Admin" },
      }));
      toast.success(`Absence note saved and locked for ${record.studentName}.`);
      if (reloadAbsentees) reloadAbsentees();
      if (reloadSections) reloadSections();
      if (reloadYears) reloadYears();
    } catch (err: any) {
      toast.error(err.message || "Failed to save absence reason.");
    } finally {
      setSavingId(null);
    }
  };

  const handleSavePlannedReason = async (record: AbsenteeStudentItem) => {
    const recordId = record.id || (record as any)._id || record.rollNumber;
    const reasonText = reasonInputs[recordId] ?? record.reason ?? "";
    if (!reasonText.trim()) {
      toast.error("Please enter a reason before saving planned absence.");
      return;
    }
    const dates = dateRanges[recordId] || { from: todayStr, to: todayStr };
    if (!dates.from || !dates.to) {
      toast.error("Please select both From and To dates.");
      return;
    }
    if (dates.from > dates.to) {
      toast.error("From Date cannot be after To Date.");
      return;
    }

    setSavingId(recordId);
    try {
      await createPlannedAbsence({
        studentId: record.studentId || recordId,
        rollNumber: record.rollNumber,
        studentName: record.studentName,
        year: record.year,
        section: record.section,
        startDate: dates.from,
        endDate: dates.to,
        reason: reasonText.trim(),
      });
      toast.success(
        `Planned leave recorded for ${record.studentName} (${dates.from} to ${dates.to}). Moved to Planned Absentees.`
      );
      if (reloadAbsentees) reloadAbsentees();
      if (reloadSections) reloadSections();
      if (reloadYears) reloadYears();
    } catch (err: any) {
      toast.error(err.message || "Failed to record planned absence.");
    } finally {
      setSavingId(null);
    }
  };

  const filteredAbsentees = useMemo(() => {
    if (!absenteesList) return [];
    const term = sectionSearch.trim().toLowerCase();
    if (!term) return absenteesList;
    return absenteesList.filter(
      (a) =>
        a.studentName.toLowerCase().includes(term) ||
        a.rollNumber.toLowerCase().includes(term) ||
        (a.studentPhone && a.studentPhone.includes(term)) ||
        (a.parentPhone && a.parentPhone.includes(term))
    );
  }, [absenteesList, sectionSearch]);

  const isGlobalSearchActive = !selectedSection && globalSearch.trim().length >= 2;

  return (
    <AdminLayout>
      <PageHeader
        title="Student Absentees"
        description="Inspect today's absentee students across academic years and sections, track dialer calls, and inspect recorded mentor notes."
        actions={
          <div className="flex items-center gap-2">
            {selectedSection ? (
              <Button variant="outline" size="sm" onClick={() => handleSelectSection(null)}>
                <ArrowLeft className="size-4 mr-2" /> Back to Sections
              </Button>
            ) : selectedYear ? (
              <Button variant="outline" size="sm" onClick={() => handleSelectYear(null)}>
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

      {/* GLOBAL SEARCH ACTIVE RESULTS */}
      {isGlobalSearchActive && (
        <div className="space-y-4 mb-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Search Results for &ldquo;{globalSearch}&rdquo;
            </h2>
            <span className="text-xs text-muted-foreground">
              {searchResults?.length || 0} student(s) found
            </span>
          </div>

          {loadingGlobalSearch ? (
            <LoadingState label="Searching students across database..." />
          ) : !searchResults || searchResults.length === 0 ? (
            <EmptyState
              title="No students found"
              description={`No student matching "${globalSearch}" was found.`}
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
              {searchResults.map((st: StudentItem) => (
                <Card
                  key={st.rollNumber}
                  className="hover:border-primary transition-all cursor-pointer"
                  onClick={() => {
                    setActiveHistoryStudent({
                      id: st.id,
                      rollNumber: st.rollNumber,
                      studentName: st.name,
                      year: st.year || selectedYear || "2nd Year",
                      section: st.section || "A",
                      ...(st.studentPhone !== undefined && { studentPhone: st.studentPhone }),
                      ...(st.parentPhone !== undefined && { parentPhone: st.parentPhone }),
                      date: todayStr,
                      status: "Absent",
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
            <ErrorState title="Failed to load years" description={errorYears} retry={reloadYears} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {normalizedYears.map((item) => (
                <Card
                  key={item.year}
                  onClick={() => handleSelectYear(item.year)}
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
                    {!!item.unassignedStudentCount && (
                      <p className="text-xs text-amber-700">
                        {item.unassignedStudentCount} student(s) have no matching section in the uploaded timetables.
                      </p>
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

      {/* LEVEL 2: Dynamic Sections for Selected Year (Strict assigned sections only, no spurious absentee cards) */}
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
            <ErrorState title="Failed to load sections" description={errorSections} retry={reloadSections} />
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
                  onClick={() => handleSelectSection(sec.section)}
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
                      View Absentees <ChevronRight className="size-4 ml-1" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* LEVEL 3: Marked Absentees for Selected Year & Section */}
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
                {filteredAbsentees.length} absentee(s) reported today
              </span>
            </div>

            <div className="flex items-center gap-3 flex-1 justify-end">
              <div className="relative max-w-xs w-full">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Filter by name, roll, or phone..."
                  value={sectionSearch}
                  onChange={(e) => setSectionSearch(e.target.value)}
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
                    { key: "date", header: "Date" },
                    { key: "reason", header: "Absence Reason", transform: (v: any) => v || "Unspecified" },
                    { key: "reasonUpdatedBy", header: "Reason Recorded By", transform: (v: any) => v || "None" },
                    { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
                    { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
                  ];
                  exportToCSV(
                    filteredAbsentees,
                    `Today_Absentees_${selectedYear.replace(/\s+/g, "_")}_Section_${selectedSection}`,
                    cols
                  );
                }}
                disabled={filteredAbsentees.length === 0}
                className="gap-1.5 bg-emerald-600/10 text-emerald-600 hover:bg-emerald-600/20 border-emerald-500/30"
                title="Export absentees to Excel/CSV"
              >
                <Download className="size-4" /> Export Absentees
              </Button>
            </div>
          </div>

          {loadingAbsentees ? (
            <LoadingState label="Loading marked absentees for section..." />
          ) : errorAbsentees ? (
            <ErrorState title="Failed to load absentees" description={errorAbsentees} retry={reloadAbsentees} />
          ) : !absenteesList || absenteesList.length === 0 ? (
            <EmptyState
              title="All Students Present!"
              description={`No absentees reported today for ${selectedYear} Section ${selectedSection}.`}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredAbsentees.map((record) => {
                const recordId = record.id || (record as any)._id || record.rollNumber;
                const isStudentCalled = calledMap[recordId]?.student;
                const isParentCalled = calledMap[recordId]?.parent;

                const lockedInfo = lockedReasonMap[recordId] || lockedReasonMap[record.rollNumber];
                const isReasonLocked = Boolean(
                  (record.reason && record.reason.trim()) ||
                  (lockedInfo && lockedInfo.reason && lockedInfo.reason.trim())
                );
                const effectiveReason = lockedInfo?.reason || record.reason || "";
                const effectiveUpdatedBy = lockedInfo?.updatedBy || record.reasonUpdatedBy || "Mentor";

                const mode = absenceModes[recordId] || "NORMAL";
                const dates = dateRanges[recordId] || { from: todayStr, to: todayStr };
                const reasonText = reasonInputs[recordId] ?? record.reason ?? "";
                const isSaving = savingId === recordId;

                return (
                  <Card key={recordId} className="border-rose-500/25 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-base font-bold">{record.studentName}</CardTitle>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="font-mono text-xs font-semibold text-primary">
                              {record.rollNumber}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {record.year} &bull; {record.section}
                            </Badge>
                          </div>
                        </div>
                        <Badge variant="destructive" className="gap-1">
                          <UserX className="size-3" /> Absent
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4 text-sm">
                      <div className="flex items-center gap-4 text-xs text-muted-foreground border-y py-2">
                        <div className="flex items-center gap-1">
                          <Calendar className="size-3.5" />
                          <span>Date: {record.date}</span>
                        </div>
                        {record.submittedBy && (
                          <div className="flex items-center gap-1">
                            <Clock className="size-3.5" />
                            <span>By: {record.submittedBy}</span>
                          </div>
                        )}
                      </div>

                      {/* Phone Dialers */}
                      <div className="grid grid-cols-2 gap-2">
                        {record.studentPhone ? (
                          <a
                            href={`tel:${record.studentPhone}`}
                            onClick={() => handleCallToggle(recordId, "student")}
                            className={cn(
                              "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-colors duration-200",
                              isStudentCalled
                                ? "bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 hover:bg-emerald-900/90 shadow-inner"
                                : "bg-emerald-600 text-white hover:bg-emerald-700"
                            )}
                            title={`Call Student (${record.studentPhone})`}
                          >
                            {isStudentCalled ? (
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

                        {record.parentPhone ? (
                          <a
                            href={`tel:${record.parentPhone}`}
                            onClick={() => handleCallToggle(recordId, "parent")}
                            className={cn(
                              "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold transition-colors duration-200",
                              isParentCalled
                                ? "bg-blue-950/80 text-blue-300 border border-blue-500/50 hover:bg-blue-900/90 shadow-inner"
                                : "bg-blue-600 text-white hover:bg-blue-700"
                            )}
                            title={`Call Parent (${record.parentPhone})`}
                          >
                            {isParentCalled ? (
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

                      {/* Dual Mode Reason Section */}
                      <div className="space-y-2.5 pt-1 border-t">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-semibold text-foreground">
                            Absence Category:
                          </label>
                          {isReasonLocked ? (
                            <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-400 gap-1 font-semibold">
                              <CheckCircle2 className="size-3 text-emerald-600" /> Normal Absence (Locked)
                            </Badge>
                          ) : (
                            <div className="inline-flex rounded-lg p-0.5 bg-muted text-[11px] border">
                              <button
                                type="button"
                                onClick={() => handleModeChange(recordId, "NORMAL")}
                                className={cn(
                                  "px-2.5 py-1 rounded-md transition-all font-medium",
                                  mode === "NORMAL"
                                    ? "bg-background text-foreground shadow-sm font-semibold"
                                    : "text-muted-foreground hover:text-foreground"
                                )}
                              >
                                Normal Absence
                              </button>
                              <button
                                type="button"
                                onClick={() => handleModeChange(recordId, "PLANNED")}
                                className={cn(
                                  "px-2.5 py-1 rounded-md transition-all font-medium",
                                  mode === "PLANNED"
                                    ? "bg-background text-amber-600 dark:text-amber-400 shadow-sm font-semibold"
                                    : "text-muted-foreground hover:text-foreground"
                                )}
                              >
                                Planned Absence
                              </button>
                            </div>
                          )}
                        </div>

                        {isReasonLocked ? (
                          <div className="space-y-2">
                            <div className="rounded-lg border border-emerald-500/40 bg-emerald-50/70 dark:bg-emerald-950/25 p-3 text-xs space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1.5 font-semibold text-emerald-800 dark:text-emerald-300">
                                  <CheckCircle2 className="size-4 text-emerald-600 shrink-0" />
                                  <span>Absence Reason Recorded</span>
                                </div>
                                <Badge variant="outline" className="text-[10px] bg-background text-emerald-700 dark:text-emerald-400 border-emerald-400 gap-1 font-semibold">
                                  <Lock className="size-3" /> Locked
                                </Badge>
                              </div>
                              <div className="bg-background/95 rounded border p-2 text-foreground font-medium italic text-xs leading-relaxed">
                                &ldquo;{effectiveReason}&rdquo;
                              </div>
                              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-0.5">
                                <span>
                                  Recorded by: <strong className="text-foreground">{effectiveUpdatedBy}</strong>
                                </span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                  Resubmission disabled
                                </span>
                              </div>
                            </div>
                            <Button
                              disabled
                              size="sm"
                              variant="outline"
                              className="w-full text-xs cursor-not-allowed opacity-80 bg-muted/40 border-muted text-muted-foreground"
                            >
                              <Lock className="size-3.5 mr-1.5" />
                              Reason Saved & Locked (Cannot Resubmit)
                            </Button>
                          </div>
                        ) : mode === "NORMAL" ? (
                          <div className="space-y-1.5">
                            <div className="flex gap-2">
                              <Input
                                placeholder="Enter reason for today only (e.g. Sick, Urgent work)..."
                                value={reasonText}
                                onChange={(e) => handleReasonChange(recordId, e.target.value)}
                                className="text-xs"
                              />
                              <Button
                                size="sm"
                                onClick={() => handleSaveNormalReason(record)}
                                disabled={isSaving}
                                className="shrink-0"
                              >
                                <Save className="size-3.5 mr-1" />
                                {isSaving ? "Saving..." : "Save Note"}
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <label className="text-[11px] font-semibold text-foreground block mb-1">
                                  From Date:
                                </label>
                                <Input
                                  type="date"
                                  value={dates.from}
                                  onChange={(e) => handleDateChange(recordId, "from", e.target.value)}
                                  className="text-xs h-8 bg-background"
                                />
                              </div>
                              <div>
                                <label className="text-[11px] font-semibold text-foreground block mb-1">
                                  To Date:
                                </label>
                                <Input
                                  type="date"
                                  value={dates.to}
                                  onChange={(e) => handleDateChange(recordId, "to", e.target.value)}
                                  className="text-xs h-8 bg-background"
                                />
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Input
                                placeholder="Planned absence reason (e.g. Medical leave, Sports competition)..."
                                value={reasonText}
                                onChange={(e) => handleReasonChange(recordId, e.target.value)}
                                className="text-xs bg-background"
                              />
                              <Button
                                size="sm"
                                onClick={() => handleSavePlannedReason(record)}
                                disabled={isSaving}
                                className="shrink-0 bg-amber-600 hover:bg-amber-700 text-white"
                              >
                                <CalendarClock className="size-3.5 mr-1" />
                                {isSaving ? "Saving..." : "Save Planned Leave"}
                              </Button>
                            </div>
                            <p className="text-[11px] text-amber-700 dark:text-amber-400">
                              &bull; Recording planned leave suppresses daily dialer prompts and moves this student to Planned Absentees.
                            </p>
                          </div>
                        )}
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-xs"
                        onClick={() => setActiveHistoryStudent(record)}
                      >
                        <History className="size-3.5 mr-2" /> View Student Absence History
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
      <Dialog open={!!activeHistoryStudent} onOpenChange={(open) => !open && setActiveHistoryStudent(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="size-5 text-primary" />
              <span>Attendance History: {activeHistoryStudent?.studentName}</span>
            </DialogTitle>
            <DialogDescription>
              Roll Number: <span className="font-mono font-semibold">{activeHistoryStudent?.rollNumber}</span> &bull; {activeHistoryStudent?.year} ({activeHistoryStudent?.section})
            </DialogDescription>
          </DialogHeader>

          {activeHistoryStudent && (
            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-3">
                {activeHistoryStudent.studentPhone ? (
                  <a
                    href={`tel:${activeHistoryStudent.studentPhone}`}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors"
                  >
                    <Phone className="size-3.5" /> Call Student ({activeHistoryStudent.studentPhone})
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Student Phone
                  </Button>
                )}

                {activeHistoryStudent.parentPhone ? (
                  <a
                    href={`tel:${activeHistoryStudent.parentPhone}`}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
                  >
                    <PhoneCall className="size-3.5" /> Call Parent ({activeHistoryStudent.parentPhone})
                  </a>
                ) : (
                  <Button variant="outline" size="sm" disabled className="text-xs">
                    No Parent Phone
                  </Button>
                )}
              </div>

              <div className="rounded-lg border bg-card">
                <div className="p-3 border-b bg-muted/40 font-semibold text-xs flex justify-between items-center">
                  <span>Logged Absence Records</span>
                  <Badge variant="outline">{historyRecords?.length || 0} Incident(s)</Badge>
                </div>
                <div className="divide-y max-h-60 overflow-y-auto">
                  {loadingHistory ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">Loading history...</div>
                  ) : !historyRecords || historyRecords.length === 0 ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">No absence history recorded for this student.</div>
                  ) : (
                    historyRecords.map((item, idx) => (
                      <div key={idx} className="p-3 text-xs space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-foreground flex items-center gap-1.5">
                            <Calendar className="size-3 text-muted-foreground" /> {item.date}
                          </span>
                          <Badge variant="destructive" className="text-[10px]">
                            {item.status}
                          </Badge>
                        </div>
                        {item.reason && (
                          <p className="text-muted-foreground bg-muted/30 p-2 rounded italic text-[11px]">
                            Note: {item.reason} {item.reasonUpdatedBy ? `(${item.reasonUpdatedBy})` : ""}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
