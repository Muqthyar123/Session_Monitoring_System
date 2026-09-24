import { useState, useEffect, useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, FileSpreadsheet, Trash2 } from "lucide-react";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { FileUpload } from "@/components/common/FileUpload";
import { DataTable, type Column } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  deleteAllTimetables,
  deleteSectionTimetable,
  downloadTimetableTemplate,
  getTimetable,
  getTimetableUploads,
  resetAllTimetables,
  uploadTimetable,
} from "@/services/timetableService";
import { toast } from "sonner";
import { MOCK_SECTIONS, MOCK_YEARS, type TimetableUpload } from "@/data/mock/mockData";

export const Route = createFileRoute("/admin/timetable")({
  head: () => ({
    meta: [
      { title: "Timetable Management — Faculty Attendance Monitor" },
      { name: "description", content: "Upload class timetables, download the template and view section timetables." },
      { property: "og:title", content: "Timetable Management — Faculty Attendance Monitor" },
      { property: "og:description", content: "Upload and view class timetables by year and section." },
    ],
  }),
  component: TimetablePage,
});

function TimetablePage() {
  const uploads = useAsyncData(() => getTimetableUploads(), []);
  const [year, setYear] = useState(MOCK_YEARS[1] || "2nd Year");

  const romanMap: Record<string, string> = {
    "1st Year": "I",
    "2nd Year": "II",
    "3rd Year": "III",
    "4th Year": "IV",
  };

  const availableSections = useMemo(() => {
    const uploadedForYear = (uploads.data ?? [])
      .filter((u) => u.academicYear === year)
      .map((u) => u.section);
    return Array.from(new Set(uploadedForYear)).sort();
  }, [uploads.data, year]);

  const [section, setSection] = useState("");

  useEffect(() => {
    if (availableSections.length > 0 && (!section || !availableSections.includes(section))) {
      setSection(availableSections[0]);
    } else if (availableSections.length === 0 && section !== "") {
      setSection("");
    }
  }, [availableSections, section]);

  const timetable = useAsyncData(() => {
    if (!section) return Promise.resolve([]);
    return getTimetable(year, section);
  }, [year, section]);

  const handleYearChange = (newYear: string) => {
    setYear(newYear);
    const uploadedForNewYear = (uploads.data ?? [])
      .filter((u) => u.academicYear === newYear)
      .map((u) => u.section);
    const sectionsForNewYear = Array.from(new Set(uploadedForNewYear)).sort();
    setSection(sectionsForNewYear[0] || "");
  };

  const handleUploadSuccess = async (file: File) => {
    const result = await uploadTimetable(file);
    uploads.reload();
    timetable.reload();
    return result;
  };

  const uploadColumns: Column<TimetableUpload>[] = [
    { key: "academicYear", header: "Academic Year", cell: (r) => r.academicYear },
    { key: "section", header: "Section", cell: (r) => r.section },
    {
      key: "file",
      header: "File",
      cell: (r) => (
        <span className="flex items-center gap-2">
          <FileSpreadsheet className="size-4 text-muted-foreground" />
          <span className="truncate">{r.file}</span>
        </span>
      ),
    },
    { key: "uploadedDate", header: "Uploaded Date", cell: (r) => r.uploadedDate },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (r.academicYear) setYear(r.academicYear);
              setSection(r.section);
              document.getElementById("timetable-view")?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            View
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive border-destructive/30 hover:bg-destructive/10"
            onClick={async () => {
              if (confirm(`Are you sure you want to delete the timetable for section ${r.section}?`)) {
                await deleteSectionTimetable(r.section);
                uploads.reload();
                timetable.reload();
              }
            }}
          >
            <Trash2 className="size-3.5 mr-1" /> Delete
          </Button>
        </div>
      ),
    },
  ];

  const days = Array.from(new Set((timetable.data ?? []).map((p) => p.day)));

  return (
    <AdminLayout>
      <PageHeader
        title="Timetable Management"
        description="Upload the college timetable workbook. Parsing is performed by the backend."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={downloadTimetableTemplate}>
              <Download className="size-4 mr-1.5" /> Download Timetable Template
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirm("Reset Timetables: Are you sure you want to delete all timetables from MongoDB database?")) {
                  try {
                    await resetAllTimetables();
                    toast.success("Timetables reset successfully: Deleted from database.");
                    uploads.reload();
                    timetable.reload();
                  } catch (err: any) {
                    toast.error(err.message || "Failed to reset timetables.");
                  }
                }
              }}
            >
              <Trash2 className="size-4 mr-1.5" /> Reset Timetables
            </Button>
          </div>
        }
      />

      <Card id="timetable-upload">
        <CardHeader>
          <CardTitle className="text-base">Upload Timetable</CardTitle>
          <CardDescription>
            Upload section timetable workbook (supports Matrix Grid format or standard 9-column template).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FileUpload onUpload={handleUploadSuccess} />
        </CardContent>
      </Card>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Uploaded Timetables</h2>
          {(uploads.data?.length ?? 0) > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="text-destructive border-destructive/30 hover:bg-destructive/10"
              onClick={async () => {
                if (confirm("Are you sure you want to delete ALL uploaded timetables?")) {
                  await deleteAllTimetables();
                  uploads.reload();
                  timetable.reload();
                }
              }}
            >
              <Trash2 className="size-3.5 mr-1" /> Clear All Timetables
            </Button>
          ) : null}
        </div>

        {uploads.loading ? (
          <LoadingState rows={3} />
        ) : uploads.error ? (
          <ErrorState message={uploads.error} onRetry={uploads.reload} />
        ) : (uploads.data?.length ?? 0) === 0 ? (
          <EmptyState title="No timetables uploaded" description="Upload a timetable workbook to get started." />
        ) : (
          <DataTable columns={uploadColumns} rows={uploads.data ?? []} getRowId={(r) => r.id} />
        )}
      </section>

      <section id="timetable-view" className="space-y-3">
        <h2 className="text-base font-semibold">Timetable View</h2>
        <div className="flex flex-wrap gap-3">
          <div className="w-full sm:w-48">
            <Select value={year} onValueChange={handleYearChange}>
              <SelectTrigger aria-label="Select Year">
                <SelectValue placeholder="Select Year" />
              </SelectTrigger>
              <SelectContent>
                {MOCK_YEARS.map((y) => (
                  <SelectItem key={y} value={y}>
                    {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-full sm:w-48">
            <Select value={section} onValueChange={setSection} disabled={availableSections.length === 0}>
              <SelectTrigger aria-label="Select Section">
                <SelectValue placeholder={availableSections.length === 0 ? "No uploaded sections" : "Select Section"} />
              </SelectTrigger>
              <SelectContent>
                {availableSections.length === 0 ? (
                  <SelectItem value="none" disabled>
                    No uploaded sections
                  </SelectItem>
                ) : (
                  availableSections.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        {timetable.loading ? (
          <LoadingState rows={4} />
        ) : timetable.error ? (
          <ErrorState message={timetable.error} onRetry={timetable.reload} />
        ) : (timetable.data?.length ?? 0) === 0 ? (
          <EmptyState
            title={`No timetable available for ${year}`}
            description={
              availableSections.length === 0
                ? `No timetable workbook has been uploaded for ${year} yet.`
                : `No timetable data available for section ${section}.`
            }
          />
        ) : (
          <div className="space-y-4">
            {days.map((day) => (
              <div key={day} className="overflow-x-auto rounded-lg border border-border bg-card">
                <div className="border-b border-border px-4 py-2 text-sm font-semibold">{day}</div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Period</TableHead>
                      <TableHead>Start</TableHead>
                      <TableHead>End</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Faculty</TableHead>
                      <TableHead>Room / Lab</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(timetable.data ?? [])
                      .filter((p) => p.day === day)
                      .map((p) => (
                        <TableRow key={`${day}-${p.period}`}>
                          <TableCell>{p.period}</TableCell>
                          <TableCell>{p.startTime}</TableCell>
                          <TableCell>{p.endTime}</TableCell>
                          <TableCell className="font-medium">{p.subject}</TableCell>
                          <TableCell className="text-muted-foreground">{p.faculty || "-"}</TableCell>
                          <TableCell>{p.room || "-"}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </div>
            ))}
          </div>
        )}
      </section>
    </AdminLayout>
  );
}
