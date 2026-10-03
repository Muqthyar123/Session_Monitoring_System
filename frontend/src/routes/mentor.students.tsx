import { useMemo, useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Users,
  Search,
  ArrowLeft,
  ChevronRight,
  GraduationCap,
  Layers,
  Phone,
  RotateCcw,
  X,
} from "lucide-react";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { DataTable, type Column } from "@/components/common/DataTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getMentorStudents,
  getMentorStudentsSections,
  getMentorStudentsYears,
  searchMentorStudentsGlobal,
  type MentorSectionCardItem,
  type MentorYearCardItem,
} from "@/services/mentorService";
import type { StudentItem } from "@/services/studentService";

export const Route = createFileRoute("/mentor/students")({
  head: () => ({
    meta: [
      { title: "All Students — Mentor Portal" },
      { name: "description", content: "Explore all enrolled students across academic years and sections with global search." },
    ],
  }),
  component: MentorStudentsPage,
});

export function computeYearFromBatch(batch?: number): string {
  if (!batch) return "—";
  const map: Record<number, string> = {
    2027: "4th Year",
    2028: "3rd Year",
    2029: "2nd Year",
    2030: "1st Year",
  };
  if (map[batch]) return map[batch];
  const yr = 2031 - batch;
  if (yr >= 1 && yr <= 4) {
    const suffixes: Record<number, string> = { 1: "1st Year", 2: "2nd Year", 3: "3rd Year", 4: "4th Year" };
    return suffixes[yr] || `${yr}th Year`;
  }
  return "Unknown";
}

function MentorStudentsPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [globalSearch, setGlobalSearch] = useState("");
  const [searchResults, setSearchResults] = useState<StudentItem[] | null>(null);
  const [searching, setSearching] = useState(false);

  // LEVEL 1: Dynamic Years
  const {
    data: yearCards,
    loading: loadingYears,
    error: errorYears,
    reload: reloadYears,
  } = useAsyncData(() => getMentorStudentsYears(), []);

  // LEVEL 2: Dynamic Sections for Selected Year
  const {
    data: sectionCards,
    loading: loadingSections,
    error: errorSections,
    reload: reloadSections,
  } = useAsyncData(
    () => (selectedYear ? getMentorStudentsSections(selectedYear) : Promise.resolve([])),
    [selectedYear]
  );

  // LEVEL 3: Students in Selected Year & Section
  const {
    data: studentsData,
    loading: loadingStudents,
    error: errorStudents,
    reload: reloadStudents,
  } = useAsyncData(
    () =>
      selectedYear && selectedSection
        ? getMentorStudents(selectedYear, selectedSection)
        : Promise.resolve([]),
    [selectedYear, selectedSection]
  );

  // Local section filter search
  const [sectionSearch, setSectionSearch] = useState("");
  const filteredSectionStudents = useMemo(() => {
    if (!studentsData) return [];
    const term = sectionSearch.trim().toLowerCase();
    if (!term) return studentsData;
    return studentsData.filter(
      (s) =>
        s.name.toLowerCase().includes(term) ||
        s.rollNumber.toLowerCase().includes(term) ||
        (s.studentPhone && s.studentPhone.includes(term)) ||
        (s.parentPhone && s.parentPhone.includes(term))
    );
  }, [studentsData, sectionSearch]);

  // Handle Global Search with Debounce
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
        const results = await searchMentorStudentsGlobal(term);
        setSearchResults(results);
      } catch (err) {
        console.error("Global search error:", err);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [globalSearch]);

  const studentColumns: Column<StudentItem>[] = [
    {
      key: "rollNumber",
      header: "Roll Number",
      cell: (r) => <span className="font-mono font-semibold text-primary">{r.rollNumber}</span>,
    },
    { key: "name", header: "Student Name" },
    {
      key: "batch",
      header: "Batch",
      cell: (r) => (
        <span className="font-mono font-medium text-xs bg-muted px-2 py-0.5 rounded">
          {r.batch || "—"}
        </span>
      ),
    },
    {
      key: "year",
      header: "Academic Year",
      cell: (r) => (
        <span className="font-medium text-xs text-foreground">
          {r.year || computeYearFromBatch(r.batch)}
        </span>
      ),
    },
    {
      key: "branch",
      header: "Branch",
      cell: (r) => <span className="text-xs font-semibold">{r.branch || "CSE"}</span>,
    },
    { key: "section", header: "Section" },
    {
      key: "studentPhone",
      header: "Student Phone",
      cell: (r) =>
        r.studentPhone ? (
          <a
            href={`tel:${r.studentPhone}`}
            className="inline-flex items-center gap-1 font-mono text-xs text-emerald-600 dark:text-emerald-400 hover:underline font-medium"
            title={`Call Student (${r.studentPhone})`}
          >
            <Phone className="size-3 text-emerald-600 dark:text-emerald-400" />
            {r.studentPhone}
          </a>
        ) : (
          <span className="text-muted-foreground font-mono text-xs">N/A</span>
        ),
    },
    {
      key: "parentPhone",
      header: "Parent Phone",
      cell: (r) =>
        r.parentPhone ? (
          <a
            href={`tel:${r.parentPhone}`}
            className="inline-flex items-center gap-1 font-mono text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
            title={`Call Parent (${r.parentPhone})`}
          >
            <Phone className="size-3 text-blue-600 dark:text-blue-400" />
            {r.parentPhone}
          </a>
        ) : (
          <span className="text-muted-foreground font-mono text-xs">N/A</span>
        ),
    },
    {
      key: "crlrName",
      header: "Assigned CR/LR",
      cell: (r) => (
        <span className="text-xs text-muted-foreground">
          {r.crlrName ? (
            <span className="font-medium text-foreground bg-accent/60 px-2 py-0.5 rounded">
              {r.crlrName}
            </span>
          ) : (
            "—"
          )}
        </span>
      ),
    },
  ];

  return (
    <MentorLayout>
      <PageHeader
        title="All Students Directory"
        description="Hierarchical exploration of enrolled students by Year & Section, with global name and roll number search."
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
        {/* Global Student Search Bar */}
        <Card className="border-primary/20 bg-muted/20">
          <CardContent className="p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Global Student Search across all years & sections (e.g. Rahul, 24471A0575)..."
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
                    <span>Searching...</span>
                  ) : (
                    <span>Found {searchResults?.length || 0} matching students</span>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Global Search Results View */}
        {globalSearch.trim().length > 0 && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Search className="size-4 text-primary" /> Global Search Results
                </CardTitle>
                <CardDescription className="text-xs">
                  Showing students matching "{globalSearch}" across all academic years and sections.
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setGlobalSearch("")}>
                Close Search
              </Button>
            </CardHeader>
            <CardContent>
              {searching ? (
                <LoadingState label="Searching all students..." />
              ) : !searchResults || searchResults.length === 0 ? (
                <EmptyState
                  title="No matching students found"
                  description={`No student records match "${globalSearch}". Please check spelling or roll number.`}
                />
              ) : (
                <DataTable
                  columns={studentColumns}
                  data={searchResults}
                  getRowId={(r) => r.id || (r as any)._id || r.rollNumber}
                />
              )}
            </CardContent>
          </Card>
        )}

        {/* LEVEL 1: Academic Year Cards (When NOT searching and NO year selected) */}
        {!globalSearch.trim() && !selectedYear && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight">Select Academic Year</h2>
              <span className="text-xs text-muted-foreground">Click a card to browse sections</span>
            </div>

            {loadingYears ? (
              <LoadingState label="Loading academic years..." />
            ) : errorYears ? (
              <ErrorState title="Failed to load years" description={errorYears.message} retry={reloadYears} />
            ) : !yearCards || yearCards.length === 0 ? (
              <EmptyState
                title="No academic years available"
                description="No student records have been uploaded to the system yet."
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
                      <div className="flex items-center justify-between">
                        <span className="text-2xl font-extrabold text-foreground">{yc.studentCount}</span>
                        <span className="text-xs text-muted-foreground">Students</span>
                      </div>
                      <div className="mt-4 flex items-center justify-end text-xs font-semibold text-primary">
                        Browse Sections <ChevronRight className="size-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LEVEL 2: Section Cards for Selected Year */}
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
                title={`No sections found for ${selectedYear}`}
                description="There are currently no students registered under this academic year."
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
                    className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                  >
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                      <div>
                        <CardTitle className="text-lg font-bold">{selectedYear}</CardTitle>
                        <CardDescription className="text-sm font-semibold text-foreground mt-0.5">
                          Section {sc.section}
                        </CardDescription>
                      </div>
                      <Layers className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    </CardHeader>
                    <CardContent className="pt-2">
                      <div className="flex items-center justify-between border-t pt-3">
                        <span className="text-xs text-muted-foreground">Enrolled Students:</span>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {sc.studentCount} Students
                        </Badge>
                      </div>
                      <div className="mt-3 flex items-center justify-end text-xs font-semibold text-primary">
                        View Students <ChevronRight className="size-4 ml-1" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* LEVEL 3: Section Students Directory Table */}
        {!globalSearch.trim() && selectedYear && selectedSection && (
          <Card>
            <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-sm font-semibold">
                    {selectedYear}
                  </Badge>
                  <Badge variant="default" className="text-sm font-semibold">
                    Section {selectedSection}
                  </Badge>
                </div>
                <CardDescription className="mt-1.5">
                  Complete enrolled student roster with contact dialers and CR/LR mapping.
                </CardDescription>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="relative min-w-[220px]">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search in this section..."
                    value={sectionSearch}
                    onChange={(e) => setSectionSearch(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Button variant="outline" size="sm" onClick={reloadStudents}>
                  <RotateCcw className="size-4 mr-2" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingStudents ? (
                <LoadingState label="Loading students..." />
              ) : errorStudents ? (
                <ErrorState title="Failed to load students" description={errorStudents.message} retry={reloadStudents} />
              ) : filteredSectionStudents.length === 0 ? (
                <EmptyState
                  title="No students found"
                  description={
                    sectionSearch
                      ? `No students in ${selectedYear} Section ${selectedSection} match "${sectionSearch}".`
                      : `No students enrolled in ${selectedYear} Section ${selectedSection}.`
                  }
                />
              ) : (
                <DataTable
                  columns={studentColumns}
                  data={filteredSectionStudents}
                  getRowId={(r) => r.id || (r as any)._id || r.rollNumber}
                />
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </MentorLayout>
  );
}
