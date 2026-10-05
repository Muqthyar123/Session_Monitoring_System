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
} from "lucide-react";
import { toast } from "sonner";
import { exportToCSV } from "@/utils/exportUtils";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
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
import type { AbsenteeStudentItem } from "@/services/studentAttendanceService";

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
    [selectedYear, selectedSection]
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

  // Absence comment states
  const [reasonInputs, setReasonInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const handleReasonChange = (id: string, value: string) => {
    setReasonInputs((prev) => ({ ...prev, [id]: value }));
  };

  const handleSaveReason = async (record: AbsenteeStudentItem) => {
    const recordId = record.id || (record as any)._id || record.rollNumber;
    const reasonText = reasonInputs[recordId] ?? record.reason ?? "";
    if (!reasonText.trim()) {
      toast.error("Please enter a reason or note before saving.");
      return;
    }

    setSavingId(recordId);
    try {
      await saveAbsenceComment(recordId, reasonText.trim());
      toast.success(`Absence note saved for ${record.studentName}.`);
      if (reloadAbsentees) reloadAbsentees();
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
                  const recordId = record.id || (record as any)._id || record.rollNumber;
                  const currentReason =
                    reasonInputs[recordId] !== undefined
                      ? reasonInputs[recordId]
                      : record.reason || "";
                  const isSaving = savingId === recordId;

                  return (
                    <Card key={recordId} className="border-rose-500/30 shadow-sm">
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

                        {/* Contact Dialers */}
                        <div className="grid grid-cols-2 gap-2">
                          {record.studentPhone ? (
                            <a
                              href={`tel:${record.studentPhone}`}
                              className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors"
                            >
                              <Phone className="size-3.5" /> Call Student
                            </a>
                          ) : (
                            <Button variant="outline" size="sm" disabled className="text-xs">
                              No Student Phone
                            </Button>
                          )}

                          {record.parentPhone ? (
                            <a
                              href={`tel:${record.parentPhone}`}
                              className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
                            >
                              <PhoneCall className="size-3.5" /> Call Parent
                            </a>
                          ) : (
                            <Button variant="outline" size="sm" disabled className="text-xs">
                              No Parent Phone
                            </Button>
                          )}
                        </div>

                        {/* Absence Reason Form */}
                        <div className="space-y-2 pt-1">
                          <label className="text-xs font-semibold text-foreground">
                            Absence Reason / Follow-up Notes:
                          </label>
                          <div className="flex gap-2">
                            <Input
                              placeholder="e.g. Medical emergency, Family leave..."
                              value={currentReason}
                              onChange={(e) => handleReasonChange(recordId, e.target.value)}
                              className="text-xs"
                            />
                            <Button
                              size="sm"
                              onClick={() => handleSaveReason(record)}
                              disabled={isSaving}
                              className="shrink-0"
                            >
                              <Save className="size-3.5 mr-1" />
                              {isSaving ? "Saving..." : "Save"}
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
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
              <ErrorState title="Failed to load years" description={errorYears.message} retry={reloadYears} />
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
              <ErrorState title="Failed to load sections" description={errorSections.message} retry={reloadSections} />
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
              <ErrorState title="Failed to load absentees" description={errorAbsentees.message} retry={reloadAbsentees} />
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
                  const recordId = record.id || (record as any)._id || record.rollNumber;
                  const currentReason =
                    reasonInputs[recordId] !== undefined
                      ? reasonInputs[recordId]
                      : record.reason || "";
                  const isSaving = savingId === recordId;

                  return (
                    <Card key={recordId} className="border-rose-500/25 shadow-sm">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <CardTitle className="text-base font-bold">{record.studentName}</CardTitle>
                            <p className="font-mono text-xs text-muted-foreground mt-0.5">
                              Roll No: <strong className="text-primary font-bold">{record.rollNumber}</strong>
                            </p>
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

                        {/* Contact & Phone Dialers */}
                        <div className="grid grid-cols-2 gap-2">
                          {record.studentPhone ? (
                            <a
                              href={`tel:${record.studentPhone}`}
                              className="inline-flex items-center justify-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors"
                              title={`Call Student (${record.studentPhone})`}
                            >
                              <Phone className="size-3.5" /> Call Student ({record.studentPhone})
                            </a>
                          ) : (
                            <Button variant="outline" size="sm" disabled className="text-xs">
                              No Student Phone
                            </Button>
                          )}

                          {record.parentPhone ? (
                            <a
                              href={`tel:${record.parentPhone}`}
                              className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
                              title={`Call Parent (${record.parentPhone})`}
                            >
                              <PhoneCall className="size-3.5" /> Call Parent ({record.parentPhone})
                            </a>
                          ) : (
                            <Button variant="outline" size="sm" disabled className="text-xs">
                              No Parent Phone
                            </Button>
                          )}
                        </div>

                        {/* Reason / Comment Section */}
                        <div className="space-y-2 pt-1">
                          <label className="text-xs font-semibold text-foreground">
                            Absence Reason / Follow-up Notes:
                          </label>
                          <div className="flex gap-2">
                            <Input
                              placeholder="Enter reason (e.g., Medical leave, Sick, Family event)..."
                              value={currentReason}
                              onChange={(e) => handleReasonChange(recordId, e.target.value)}
                              className="text-xs"
                            />
                            <Button
                              size="sm"
                              onClick={() => handleSaveReason(record)}
                              disabled={isSaving}
                              className="shrink-0"
                            >
                              <Save className="size-3.5 mr-1" />
                              {isSaving ? "Saving..." : "Save"}
                            </Button>
                          </div>
                          {record.reason && (
                            <p className="text-[11px] text-muted-foreground mt-1">
                              Current note: <span className="italic text-foreground font-medium">"{record.reason}"</span>
                              {record.reasonUpdatedBy && <span> (by {record.reasonUpdatedBy})</span>}
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
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
