import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, FileSpreadsheet } from "lucide-react";
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
  const [year, setYear] = useState(MOCK_YEARS[0]!);
  const [section, setSection] = useState(MOCK_SECTIONS[0]!);
  const timetable = useAsyncData(() => getTimetable(year, section), [year, section]);

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
        <div className="flex gap-2">
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
            variant="ghost"
            size="sm"
            onClick={() => document.getElementById("timetable-upload")?.scrollIntoView({ behavior: "smooth" })}
          >
            Replace
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
            Workbook format reference: All_Class_Timetables_Format.xlsx (one sheet per section).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FileUpload onUpload={uploadTimetable} />
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Uploaded Timetables</h2>
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
                {MOCK_SECTIONS.map((s) => (
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
                          <TableCell>{p.subject}</TableCell>
                          <TableCell>{p.room}</TableCell>
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
