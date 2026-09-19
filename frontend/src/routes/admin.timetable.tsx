import { useState, useEffect } from "react";
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
  uploadTimetable,
} from "@/services/timetableService";
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
  const [section, setSection] = useState("");
  const timetable = useAsyncData(() => getTimetable(year, section), [year, section]);

  useEffect(() => {
    if (uploads.data && uploads.data.length > 0) {
      const validSections = uploads.data.map((u) => u.section);
      if (!section || !validSections.includes(section)) {
        setSection(uploads.data[0].section);
        if (uploads.data[0].academicYear) {
          setYear(uploads.data[0].academicYear);
        }
      }
    }
  }, [uploads.data]);

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
          <Button variant="outline" onClick={downloadTimetableTemplate}>
            <Download className="size-4" /> Download Timetable Template
          </Button>
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
            <Select value={year} onValueChange={setYear}>
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
          <div className="w-full sm:w-40">
            <Select value={section} onValueChange={setSection}>
              <SelectTrigger aria-label="Select Section">
                <SelectValue placeholder="Select Section" />
              </SelectTrigger>
              <SelectContent>
                {(uploads.data ?? []).map((u) => u.section).concat(["II-A"]).filter((v, i, a) => a.indexOf(v) === i).map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {timetable.loading ? (
          <LoadingState rows={4} />
        ) : timetable.error ? (
          <ErrorState message={timetable.error} onRetry={timetable.reload} />
        ) : (timetable.data?.length ?? 0) === 0 ? (
          <EmptyState title="No timetable available" description="No timetable has been uploaded for this section yet." />
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
