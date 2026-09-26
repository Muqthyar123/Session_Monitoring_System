import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import {
  Phone,
  PhoneCall,
  ChevronRight,
  ArrowLeft,
  Calendar,
  GraduationCap,
  Save,
  CheckCircle,
  Clock,
  UserX,
} from "lucide-react";
import { toast } from "sonner";
import { MentorLayout } from "@/layouts/MentorLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getAbsenteeYears,
  getAbsenteeSections,
  getAbsenteeStudents,
  saveAbsenceReason,
  type AbsenteeStudentItem,
} from "@/services/studentAttendanceService";
import { MOCK_YEARS } from "@/data/mock/mockData";

export const Route = createFileRoute("/mentor/absentees")({
  head: () => ({
    meta: [
      { title: "Absentee Monitoring — Mentor Portal" },
      { name: "description", content: "Inspect absentee students, make direct phone calls, and record absence reasons." },
    ],
  }),
  component: MentorAbsenteesPage,
});

function MentorAbsenteesPage() {
  const [selectedYear, setSelectedYear] = useState<string | null>(null);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  // Fetch available years that have absentees, or fallback to standard years
  const { data: yearsData, loading: loadingYears, error: errorYears } = useAsyncData(
    () => getAbsenteeYears(),
    []
  );

  const displayYears = useMemo(() => {
    if (yearsData && yearsData.length > 0) {
      return Array.from(new Set([...yearsData, ...MOCK_YEARS])).sort();
    }
    return MOCK_YEARS;
  }, [yearsData]);

  // Fetch sections when a year is selected
  const {
    data: sectionsData,
    loading: loadingSections,
    error: errorSections,
  } = useAsyncData(
    () => (selectedYear ? getAbsenteeSections(selectedYear) : Promise.resolve([])),
    [selectedYear]
  );

  // Fetch absentees when year & section are selected
  const {
    data: absentees,
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

  const [reasonInputs, setReasonInputs] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const handleReasonChange = (id: string, value: string) => {
    setReasonInputs((prev) => ({ ...prev, [id]: value }));
  };

  const handleSaveReason = async (record: AbsenteeStudentItem) => {
    const reasonText = reasonInputs[record.id] ?? record.reason ?? "";
    setSavingId(record.id);
    try {
      await saveAbsenceReason(record.id, reasonText);
      toast.success(`Absence reason saved for ${record.studentName}.`);
      reloadAbsentees();
    } catch (err: any) {
      toast.error(err.message || "Failed to save reason.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <MentorLayout>
      <PageHeader
        title="Absentee Students Monitoring"
        description="Drill down by Year and Section to inspect absentees, place dialer calls to parents/students, and record follow-up notes."
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

      {/* LEVEL 1: Select Academic Year */}
      {!selectedYear && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold tracking-tight">Select Academic Year</h2>
          {loadingYears ? (
            <LoadingState label="Loading academic years..." />
          ) : errorYears ? (
            <ErrorState title="Failed to load years" description={errorYears.message} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {displayYears.map((year) => (
                <Card
                  key={year}
                  onClick={() => setSelectedYear(year)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-base font-bold">{year}</CardTitle>
                    <GraduationCap className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                  </CardHeader>
                  <CardContent className="pt-2">
                    <p className="text-xs text-muted-foreground">
                      Click to view sections in {year}
                    </p>
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
      {selectedYear && !selectedSection && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-sm px-3 py-1">
              {selectedYear}
            </Badge>
            <span className="text-sm text-muted-foreground">Select Section</span>
          </div>

          {loadingSections ? (
            <LoadingState label={`Loading sections for ${selectedYear}...`} />
          ) : errorSections ? (
            <ErrorState title="Failed to load sections" description={errorSections.message} />
          ) : !sectionsData || sectionsData.length === 0 ? (
            <EmptyState
              title={`No absentee records in ${selectedYear}`}
              description="There are currently no absentee records submitted for this academic year."
              action={
                <Button variant="outline" onClick={() => setSelectedYear(null)}>
                  Choose Another Year
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {sectionsData.map((sec) => (
                <Card
                  key={sec}
                  onClick={() => setSelectedSection(sec)}
                  className="cursor-pointer transition-all hover:border-primary hover:shadow-md group"
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-bold">{selectedYear} &bull; Section {sec}</CardTitle>
                    <CardDescription>Section {sec}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-end text-xs font-semibold text-primary mt-2">
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
            <span className="text-xs text-muted-foreground">
              Total Absentees: {absentees?.length || 0}
            </span>
          </div>

          {loadingAbsentees ? (
            <LoadingState label="Loading absentee details..." />
          ) : errorAbsentees ? (
            <ErrorState title="Failed to load absentees" description={errorAbsentees.message} retry={reloadAbsentees} />
          ) : !absentees || absentees.length === 0 ? (
            <EmptyState
              title="No absentees found"
              description={`No absentee records submitted for ${selectedYear} Section ${selectedSection}.`}
              action={
                <Button variant="outline" onClick={() => setSelectedSection(null)}>
                  Back to Sections
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {absentees.map((record) => {
                const currentReason =
                  reasonInputs[record.id] !== undefined
                    ? reasonInputs[record.id]
                    : record.reason || "";
                const isSaving = savingId === record.id;

                return (
                  <Card key={record.id} className="border-rose-500/20 shadow-sm">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-base font-bold">{record.studentName}</CardTitle>
                          <p className="font-mono text-xs text-muted-foreground mt-0.5">
                            Roll No: {record.rollNumber}
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

                      {/* Contact & Dialer Buttons */}
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

                      {/* Reason Form */}
                      <div className="space-y-2 pt-1">
                        <label className="text-xs font-semibold text-foreground">
                          Absence Reason / Follow-up Notes:
                        </label>
                        <div className="flex gap-2">
                          <Input
                            placeholder="Enter reason (e.g., Medical leave, Sick, Family event)..."
                            value={currentReason}
                            onChange={(e) => handleReasonChange(record.id, e.target.value)}
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
    </MentorLayout>
  );
}
