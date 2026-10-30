import { useMemo, useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Phone,
  PhoneCall,
  ChevronRight,
  ArrowLeft,
  Calendar,
  GraduationCap,
  Save,
  Clock,
  UserX,
  Search,
  RotateCcw,
  X,
  Layers,
  Download,
  CalendarClock,
  CheckCircle2,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import { exportToCSV } from "@/utils/exportUtils";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { cn } from "@/lib/utils";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getMentorAbsentees,
  getMentorAbsenteesSections,
  getMentorAbsenteesYears,
  saveAbsenceComment,
  searchMentorAbsenteesGlobal,
  type MentorSectionCardItem,
  type MentorYearCardItem,
} from "@/services/mentorService";
import { createPlannedAbsence } from "@/services/plannedAbsenceService";
import type { AbsenteeStudentItem } from "@/services/studentAttendanceService";

interface AbsenteeCardProps {
  record: AbsenteeStudentItem;
  reasonText: string;
  onReasonChange: (val: string) => void;
  isSaving: boolean;
  mode: "NORMAL" | "PLANNED";
  onModeChange: (m: "NORMAL" | "PLANNED") => void;
  fromDate: string;
  toDate: string;
  onDateChange: (field: "from" | "to", val: string) => void;
  onSaveNormal: () => void;
  onSavePlanned: () => void;
  calledState?: { student?: boolean; parent?: boolean };
  onCallToggle: (type: "student" | "parent") => void;
  lockedInfo?: { reason: string; updatedBy?: string };
}

function AbsenteeCard({
  record,
  reasonText,
  onReasonChange,
  isSaving,
  mode,
  onModeChange,
  fromDate,
  toDate,
  onDateChange,
  onSaveNormal,
  onSavePlanned,
  calledState,
  onCallToggle,
  lockedInfo,
}: AbsenteeCardProps) {
  const isStudentCalled = calledState?.student;
  const isParentCalled = calledState?.parent;

  const isReasonLocked = Boolean(
    (record.reason && record.reason.trim()) ||
    (lockedInfo && lockedInfo.reason && lockedInfo.reason.trim())
  );
  const effectiveReason = lockedInfo?.reason || record.reason || "";
  const effectiveUpdatedBy = lockedInfo?.updatedBy || record.reasonUpdatedBy || "Mentor";

  return (
    <Card className="border-rose-500/25 shadow-sm transition-all hover:shadow-md">
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
              {record.sessionId && <Badge variant="secondary" className="text-[10px]">{record.sessionId === "SESSION_1" ? "Before Lunch" : record.sessionId === "SESSION_2" ? "After Lunch" : record.sessionId}</Badge>}
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

        {/* Contact & Phone Dialers with Smooth Color Toggle */}
        <div className="grid grid-cols-2 gap-2">
          {record.studentPhone ? (
            <a
              href={`tel:${record.studentPhone}`}
              onClick={() => onCallToggle("student")}
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
              onClick={() => onCallToggle("parent")}
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
                  onClick={() => onModeChange("NORMAL")}
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
                  onClick={() => onModeChange("PLANNED")}
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
                  "{effectiveReason}"
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
                  placeholder="Enter reason for today only (e.g., Sick, Urgent work)..."
                  value={reasonText}
                  onChange={(e) => onReasonChange(e.target.value)}
                  className="text-xs"
                />
                <Button
                  size="sm"
                  onClick={onSaveNormal}
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
                    value={fromDate}
                    onChange={(e) => onDateChange("from", e.target.value)}
                    className="text-xs h-8 bg-background"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-foreground block mb-1">
                    To Date:
                  </label>
                  <Input
                    type="date"
                    value={toDate}
                    onChange={(e) => onDateChange("to", e.target.value)}
                    className="text-xs h-8 bg-background"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Planned absence reason (e.g., Medical leave, Sports competition)..."
                  value={reasonText}
                  onChange={(e) => onReasonChange(e.target.value)}
                  className="text-xs bg-background"
                />
                <Button
                  size="sm"
                  onClick={onSavePlanned}
                  disabled={isSaving}
                  className="shrink-0 bg-amber-600 hover:bg-amber-700 text-white"
                >
                  <CalendarClock className="size-3.5 mr-1" />
                  {isSaving ? "Saving..." : "Save Planned Leave"}
                </Button>
              </div>
              <p className="text-[11px] text-amber-700 dark:text-amber-400">
                &bull; Recording planned leave suppresses daily dialer prompts and moves this student to <strong>Planned Absentees</strong>.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export const Route = createFileRoute("/mentor/absentees")({
  head: () => ({
    meta: [
      { title: "Today's Absentees — Mentor Portal" },
      { name: "description", content: "Inspect today's absentee students, place direct dialer calls to parents/students, and record follow-up notes." },
    ],
  }),
  component: MentorAbsenteesPage,
});

function MentorAbsenteesPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [globalSearch, setGlobalSearch] = useState("");
  const [searchResults, setSearchResults] = useState<AbsenteeStudentItem[] | null>(null);
  const [searching, setSearching] = useState(false);

  // LEVEL 1: Fetch dynamic years with today's absentee counts
  const {
    data: yearCards,
    loading: loadingYears,
    error: errorYears,
    reload: reloadYears,
  } = useAsyncData(() => getMentorAbsenteesYears(), []);

  // LEVEL 2: Fetch dynamic sections for selected year with today's absentee counts
  const {
    data: sectionCards,
    loading: loadingSections,
    error: errorSections,
    reload: reloadSections,
  } = useAsyncData(
    () => (selectedYear ? getMentorAbsenteesSections(selectedYear) : Promise.resolve([])),
    [selectedYear]
  );

  // LEVEL 3: Fetch today's absentees for selected year & section
  const {
    data: absentees,
    loading: loadingAbsentees,
    error: errorAbsentees,
    reload: reloadAbsentees,
  } = useAsyncData(
    () =>
      selectedYear && selectedSection
        ? getMentorAbsentees(selectedYear, selectedSection)
        : Promise.resolve([]),
    [selectedYear, selectedSection],
    15000
  );

  // Local section filter search
  const [sectionSearch, setSectionSearch] = useState("");
  const filteredSectionAbsentees = useMemo(() => {
    if (!absentees) return [];
    const term = sectionSearch.trim().toLowerCase();
    if (!term) return absentees;
    return absentees.filter(
      (a) =>
        a.studentName.toLowerCase().includes(term) ||
        a.rollNumber.toLowerCase().includes(term) ||
        (a.studentPhone && a.studentPhone.includes(term)) ||
        (a.parentPhone && a.parentPhone.includes(term))
    );
  }, [absentees, sectionSearch]);

  // Global Search Debounce
  useEffect(() => {
    const term = globalSearch.trim();
    if (!term) {
      setSearchResults(null);
      setSearching(false);
      return;
    }

    setSearching(true);
    const handler = setTimeout(async () => {
      try {
        const results = await searchMentorAbsenteesGlobal(term);
        setSearchResults(results);
      } catch (err) {
        console.error("Global absentee search error:", err);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [globalSearch]);

  // Today date string (YYYY-MM-DD)
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Absence comment and mode states
  const [absenceModes, setAbsenceModes] = useState<Record<string, "NORMAL" | "PLANNED">>({});
  const [dateRanges, setDateRanges] = useState<Record<string, { from: string; to: string }>>({});
  const [reasonInputs, setReasonInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  // Permanently locked reasons map for instant dynamic UI updates without reload
  const [lockedReasonMap, setLockedReasonMap] = useState<Record<string, { reason: string; updatedBy?: string }>>({});

  // Dialer call tracker for smooth color/badge toggle
  const [calledMap, setCalledMap] = useState<Record<string, { student?: boolean; parent?: boolean }>>({});

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
    const recordId = record.id || (record as any)._id || record.rollNumber;
    const reasonText = reasonInputs[recordId] ?? record.reason ?? "";
    if (!reasonText.trim()) {
      toast.error("Please enter a reason or note before saving.");
      return;
    }

    setSavingId(recordId);
    try {
      await saveAbsenceComment(recordId, reasonText.trim());
      // Optimistically update record and locked reason map
      record.reason = reasonText.trim();
      record.reasonUpdatedBy = "Mentor";
      setLockedReasonMap((prev) => ({
        ...prev,
        [recordId]: { reason: reasonText.trim(), updatedBy: "Mentor" },
        [record.rollNumber]: { reason: reasonText.trim(), updatedBy: "Mentor" },
      }));
      toast.success(`Absence note saved and locked for ${record.studentName}.`);
      if (reloadAbsentees) reloadAbsentees();
      if (reloadSections) reloadSections();
      if (reloadYears) reloadYears();
      if (globalSearch) {
        const updated = await searchMentorAbsenteesGlobal(globalSearch.trim());
        setSearchResults(updated);
      }
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
      if (globalSearch) {
        const updated = await searchMentorAbsenteesGlobal(globalSearch.trim());
        setSearchResults(updated);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to record planned absence.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <MentorLayout>
      <PageHeader
        title="Today's Absentees"
        description="Inspect absent students, place one-click dialer phone calls to parents/students, and record absence follow-up notes."
        actions={
          selectedSection ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedSection(null)}
            >
              <ArrowLeft className="size-4 mr-2" /> Back to Sections
            </Button>
          ) : selectedYear ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedYear(null)}
            >
              <ArrowLeft className="size-4 mr-2" /> Back to Years
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-6">
        {/* Global Absentee Search Bar */}
        <Card className="border-rose-500/20 bg-rose-50/20 dark:bg-rose-950/10">
          <CardContent className="p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Global Absentee Search across all years & sections (e.g. Pallavi, 24471A0575)..."
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  className="pl-9 pr-9"
                />
                {globalSearch && (
                  <button
                    onClick={() => setGlobalSearch("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    title="Clear search"
                  >
                    <X className="size-4" />
                  </button>
                )}
              </div>
              {globalSearch && (
                <div className="text-xs text-muted-foreground">
                  {searching ? (
                    <span>Searching today's absentees...</span>
                  ) : (
                    <span>Found {searchResults?.length || 0} absent students</span>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Global Absentee Search Results View */}
        {globalSearch.trim().length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold flex items-center gap-2 text-rose-600 dark:text-rose-400">
                  <UserX className="size-4" /> Global Absentee Search Results
                </h3>
                <p className="text-xs text-muted-foreground">
                  Showing today's absent students matching "{globalSearch}".
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const absCols = [
                      { key: "date", header: "Date" },
                      { key: "rollNumber", header: "Roll Number" },
                      { key: "studentName", header: "Student Name" },
                      { key: "year", header: "Academic Year" },
                      { key: "section", header: "Section" },
                      { key: "status", header: "Status" },
                      { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
                      { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
                      {
                        key: "reason",
                        header: "Reason / Comment",
                        transform: (_: any, r: any) => reasonInputs[r.id] ?? r.reason ?? "",
                      },
                      { key: "submittedBy", header: "Submitted By", transform: (v: any) => v || "" },
                    ];
                    exportToCSV(searchResults || [], `Absentees_Search_${globalSearch.trim()}`, absCols);
                  }}
                  disabled={!searchResults || searchResults.length === 0}
                  className="gap-1.5"
                >
                  <Download className="size-4" /> Export
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setGlobalSearch("")}>
                  Close Search
                </Button>
              </div>
            </div>

            {searching ? (
              <LoadingState label="Searching today's absentees..." />
            ) : !searchResults || searchResults.length === 0 ? (
              <EmptyState
                title="No matching absentees today"
                description={`No student marked absent today matches "${globalSearch}".`}
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {searchResults.map((record) => {
                  const recordId = record.id || record._id || record.rollNumber;
                  const currentReason =
                    reasonInputs[recordId] !== undefined
                      ? reasonInputs[recordId]
                      : record.reason || "";
                  const isSaving = savingId === recordId;
                  const currentMode = absenceModes[recordId] || "NORMAL";
                  const dates = dateRanges[recordId] || { from: todayStr, to: todayStr };

                  return (
                    <AbsenteeCard
                      key={recordId}
                      record={record}
                      reasonText={currentReason}
                      onReasonChange={(val) => handleReasonChange(recordId, val)}
                      isSaving={isSaving}
                      mode={currentMode}
                      onModeChange={(m) => handleModeChange(recordId, m)}
                      fromDate={dates.from}
                      toDate={dates.to}
                      onDateChange={(field, val) => handleDateChange(recordId, field, val)}
                      onSaveNormal={() => handleSaveNormalReason(record)}
                      onSavePlanned={() => handleSavePlannedReason(record)}
                      {...(calledMap[recordId] !== undefined && { calledState: calledMap[recordId] })}
                      onCallToggle={(type) =>
                        setCalledMap((prev) => ({
                          ...prev,
                          [recordId]: { ...prev[recordId], [type]: true },
                        }))
                      }
                      {...((lockedReasonMap[recordId] || lockedReasonMap[record.rollNumber]) !== undefined && {
                        lockedInfo: lockedReasonMap[recordId] || lockedReasonMap[record.rollNumber],
                      })}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* LEVEL 1: Dynamic Academic Year Cards */}
        {!globalSearch.trim() && !selectedYear && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight">Select Academic Year</h2>
              <span className="text-xs text-muted-foreground">Click a year to view section absentees</span>
            </div>

            {loadingYears ? (
              <LoadingState label="Loading academic years..." />
            ) : errorYears ? (
              <ErrorState title="Failed to load years" description={errorYears} retry={reloadYears} />
            ) : !yearCards || yearCards.length === 0 ? (
              <EmptyState
                title="No absentees reported today"
                description="All students across all academic years are present today."
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {yearCards.map((yc) => (
                  <Card
                    key={yc.year}
                    onClick={() => setSelectedYear(yc.year)}
                    className="cursor-pointer transition-all hover:border-rose-500 hover:shadow-md group"
                  >
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-base font-bold">{yc.year}</CardTitle>
                      <GraduationCap className="size-5 text-muted-foreground group-hover:text-rose-500 transition-colors" />
                    </CardHeader>
                    <CardContent className="pt-2">
                      <div className="flex items-center justify-between">
                        <span className="text-2xl font-extrabold text-rose-600 dark:text-rose-400">
                          {yc.absenteeCount}
                        </span>
                        <Badge variant={yc.absenteeCount > 0 ? "destructive" : "outline"} className="text-xs">
                          {yc.absenteeCount} Absentees
                        </Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-2">
                        Total Enrolled: {yc.studentCount} Students
                      </p>
                      <div className="mt-4 flex items-center justify-end text-xs font-semibold text-rose-600 dark:text-rose-400">
                        View Sections <ChevronRight className="size-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LEVEL 2: Dynamic Section Cards for Selected Year */}
        {!globalSearch.trim() && selectedYear && !selectedSection && (
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
              <ErrorState title="Failed to load sections" description={errorSections} retry={reloadSections} />
            ) : !sectionCards || sectionCards.length === 0 ? (
              <EmptyState
                title={`No absentee records in ${selectedYear}`}
                description="There are currently no absentees recorded for this academic year."
                action={
                  <Button variant="outline" onClick={() => setSelectedYear(null)}>
                    Choose Another Year
                  </Button>
                }
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {sectionCards.map((sc) => (
                  <Card
                    key={sc.section}
                    onClick={() => setSelectedSection(sc.section)}
                    className="cursor-pointer transition-all hover:border-rose-500 hover:shadow-md group"
                  >
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                      <div>
                        <CardTitle className="text-lg font-bold">{selectedYear}</CardTitle>
                        <CardDescription className="text-sm font-semibold text-foreground mt-0.5">
                          Section {sc.section}
                        </CardDescription>
                      </div>
                      <Layers className="size-5 text-muted-foreground group-hover:text-rose-500 transition-colors" />
                    </CardHeader>
                    <CardContent className="pt-2">
                      <div className="flex items-center justify-between border-t pt-3">
                        <span className="text-xs text-muted-foreground">Today's Absentees:</span>
                        <Badge variant={sc.absenteeCount > 0 ? "destructive" : "secondary"} className="font-mono text-xs">
                          {sc.absenteeCount} Absent
                        </Badge>
                      </div>
                      <div className="mt-3 flex items-center justify-end text-xs font-semibold text-rose-600 dark:text-rose-400">
                        Inspect Absentees <ChevronRight className="size-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LEVEL 3: Absentees List for Selected Year & Section */}
        {!globalSearch.trim() && selectedYear && selectedSection && (
          <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-sm font-semibold">
                  {selectedYear}
                </Badge>
                <Badge variant="default" className="text-sm font-semibold">
                  Section {selectedSection}
                </Badge>
                <span className="text-xs text-muted-foreground ml-2">
                  Total Absentees: {absentees?.length || 0}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search in section..."
                    value={sectionSearch}
                    onChange={(e) => setSectionSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const absCols = [
                      { key: "date", header: "Date" },
                      { key: "rollNumber", header: "Roll Number" },
                      { key: "studentName", header: "Student Name" },
                      { key: "year", header: "Academic Year" },
                      { key: "section", header: "Section" },
                      { key: "status", header: "Status" },
                      { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
                      { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
                      {
                        key: "reason",
                        header: "Reason / Comment",
                        transform: (_: any, r: any) => reasonInputs[r.id] ?? r.reason ?? "",
                      },
                      { key: "submittedBy", header: "Submitted By", transform: (v: any) => v || "" },
                    ];
                    exportToCSV(
                      filteredSectionAbsentees,
                      `Absentees_${selectedYear.replace(/\s+/g, "_")}_Section_${selectedSection}`,
                      absCols
                    );
                  }}
                  disabled={filteredSectionAbsentees.length === 0}
                  className="gap-1.5"
                  title="Export absentees to Excel/CSV"
                >
                  <Download className="size-4" /> Export
                </Button>
                <Button variant="outline" size="sm" onClick={reloadAbsentees}>
                  <RotateCcw className="size-4 mr-2" /> Refresh
                </Button>
              </div>
            </div>

            {loadingAbsentees ? (
              <LoadingState label="Loading absentee details..." />
            ) : errorAbsentees ? (
              <ErrorState title="Failed to load absentees" description={errorAbsentees} retry={reloadAbsentees} />
            ) : !absentees || absentees.length === 0 ? (
              <EmptyState
                title="No absentees reported today"
                description={`No absentee records submitted for ${selectedYear} Section ${selectedSection}. All students are present!`}
                action={
                  <Button variant="outline" onClick={() => setSelectedSection(null)}>
                    Back to Sections
                  </Button>
                }
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {filteredSectionAbsentees.map((record) => {
                  const recordId = record.id || record._id || record.rollNumber;
                  const currentReason =
                    reasonInputs[recordId] !== undefined
                      ? reasonInputs[recordId]
                      : record.reason || "";
                  const isSaving = savingId === recordId;
                  const currentMode = absenceModes[recordId] || "NORMAL";
                  const dates = dateRanges[recordId] || { from: todayStr, to: todayStr };

                  return (
                    <AbsenteeCard
                      key={recordId}
                      record={record}
                      reasonText={currentReason}
                      onReasonChange={(val) => handleReasonChange(recordId, val)}
                      isSaving={isSaving}
                      mode={currentMode}
                      onModeChange={(m) => handleModeChange(recordId, m)}
                      fromDate={dates.from}
                      toDate={dates.to}
                      onDateChange={(field, val) => handleDateChange(recordId, field, val)}
                      onSaveNormal={() => handleSaveNormalReason(record)}
                      onSavePlanned={() => handleSavePlannedReason(record)}
                      {...(calledMap[recordId] !== undefined && { calledState: calledMap[recordId] })}
                      onCallToggle={(type) =>
                        setCalledMap((prev) => ({
                          ...prev,
                          [recordId]: { ...prev[recordId], [type]: true },
                        }))
                      }
                      {...((lockedReasonMap[recordId] || lockedReasonMap[record.rollNumber]) !== undefined && {
                        lockedInfo: lockedReasonMap[recordId] || lockedReasonMap[record.rollNumber],
                      })}
                    />
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </MentorLayout>
  );
}
