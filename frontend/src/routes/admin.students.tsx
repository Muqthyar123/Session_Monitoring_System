import { useEffect, useMemo, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, Plus, Search, Pencil, Trash2, RotateCcw, Phone, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";
import { exportToCSV } from "@/utils/exportUtils";
import { AdminLayout } from "@/layouts/AdminLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { FileUpload } from "@/components/common/FileUpload";
import { DataTable, type Column } from "@/components/common/DataTable";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAsyncData } from "@/hooks/useAsyncData";
import { ComboboxInput } from "@/components/ui/combobox-input";
import { getTimetableUploads } from "@/services/timetableService";
import {
  createStudent,
  deleteStudent,
  downloadStudentTemplate,
  resetStudents,
  updateStudent,
  uploadStudentExcel,
  getStudentsPage,
  getStudentFilterOptions,
  type StudentItem,
} from "@/services/studentService";

export const Route = createFileRoute("/admin/students")({
  head: () => ({
    meta: [
      { title: "Manage Students — Admin Portal" },
      { name: "description", content: "Upload and view uploaded student roster." },
    ],
  }),
  component: AdminStudentsPage,
});

const ALL = "ALL";
const BATCH_OPTIONS = [
  { batch: 2027, label: "2027 (4th Year)" },
  { batch: 2028, label: "2028 (3rd Year)" },
  { batch: 2029, label: "2029 (2nd Year)" },
  { batch: 2030, label: "2030 (1st Year)" },
  { batch: 2031, label: "2031 (1st Year)" },
];

export function inferBatchFromRoll(roll?: string): number | undefined {
  if (!roll) return undefined;
  const clean = roll.trim().toUpperCase();
  const m = clean.match(/^(\d{2})/);
  if (m) {
    const yearPrefix = m[1];
    if (!yearPrefix) return undefined;
    const yy = parseInt(yearPrefix, 10);
    if (yy >= 18 && yy <= 40) {
      const adm = 2000 + yy;
      const isLE = /^\d{2}[A-Z0-9]{2}[5L]/.test(clean);
      return isLE ? adm + 3 : adm + 4;
    }
  }
  return undefined;
}

export function computeYearFromBatch(batch?: number | string): string {
  if (!batch) return "—";
  const b = typeof batch === "string" ? parseInt(batch, 10) : batch;
  if (isNaN(b)) return "—";
  const now = new Date();
  const academicBase = (now.getMonth() + 1) >= 7 ? now.getFullYear() : now.getFullYear() - 1;
  const diff = b - academicBase;
  if (diff <= 0) return "Graduated";
  if (diff === 1) return "4th Year";
  if (diff === 2) return "3rd Year";
  if (diff === 3) return "2nd Year";
  if (diff >= 4) return "1st Year";
  return "—";
}


interface StudentFormState {
  name: string;
  rollNumber: string;
  batch: number;
  branch: string;
  section: string;
  studentPhone: string;
  parentPhone: string;
}

const emptyForm: StudentFormState = {
  name: "",
  rollNumber: "",
  batch: 2029,
  branch: "CSE",
  section: "CSE-J",
  studentPhone: "",
  parentPhone: "",
};

function AdminStudentsPage() {
  const [yearFilter, setYearFilter] = useState(() => {
    return sessionStorage.getItem("admin_students_year") || ALL;
  });
  const [sectionFilter, setSectionFilter] = useState(() => {
    return sessionStorage.getItem("admin_students_section") || ALL;
  });
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 25;
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [search]);

  const handleYearFilterChange = (y: string) => {
    setYearFilter(y);
    setPage(1);
    sessionStorage.setItem("admin_students_year", y);
  };

  const handleSectionFilterChange = (s: string) => {
    setSectionFilter(s);
    setPage(1);
    sessionStorage.setItem("admin_students_section", s);
  };

  const { data: pageData, loading, error, reload } = useAsyncData(
    () => getStudentsPage({ year: yearFilter, section: sectionFilter, search: debouncedSearch, page, pageSize }),
    [yearFilter, sectionFilter, debouncedSearch, page]
  );
  const { data: filterOptions } = useAsyncData(() => getStudentFilterOptions(), []);
  const data = Array.isArray(pageData) ? pageData : (pageData?.items ?? []);
  const timetableUploads = useAsyncData(() => getTimetableUploads(), []);

  const studentExportColumns = [
    { key: "rollNumber", header: "Roll Number" },
    { key: "name", header: "Student Name" },
    {
      key: "batch",
      header: "Batch",
      transform: (_: any, r: StudentItem) => r.batch || inferBatchFromRoll(r.rollNumber) || "",
    },
    {
      key: "year",
      header: "Academic Year",
      transform: (_: any, r: StudentItem) => {
        const effBatch = r.batch || inferBatchFromRoll(r.rollNumber);
        return effBatch ? computeYearFromBatch(effBatch) : (r.year || "");
      },
    },
    { key: "branch", header: "Branch", transform: (v: any) => v || "CSE" },
    { key: "section", header: "Section" },
    { key: "studentPhone", header: "Student Phone", transform: (v: any) => v || "" },
    { key: "parentPhone", header: "Parent Phone", transform: (v: any) => v || "" },
    { key: "crlrName", header: "Assigned CR/LR", transform: (v: any) => v || "" },
  ];

  const filteredStudents = data;


  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<StudentItem | null>(null);
  const [form, setForm] = useState<StudentFormState>(emptyForm);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof StudentFormState, string>>>({});
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<StudentItem | null>(null);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const formCalculatedYear = useMemo(() => {
    return computeYearFromBatch(form.batch);
  }, [form.batch]);

  // Timetable sections specifically for the selected form academic year
  const formYearSections = useMemo(() => {
    const rawYear = formCalculatedYear;
    const fromTimetable = (timetableUploads.data ?? [])
      .filter((t) => {
        if (!t.academicYear) return true;
        const aYear = t.academicYear.toLowerCase().trim();
        const curYear = rawYear.toLowerCase().trim();
        if (aYear === curYear) return true;
        if (curYear.startsWith("2") && (aYear.startsWith("2") || aYear.includes("ii"))) return true;
        if (curYear.startsWith("3") && (aYear.startsWith("3") || aYear.includes("iii"))) return true;
        if (curYear.startsWith("4") && (aYear.startsWith("4") || aYear.includes("iv"))) return true;
        if (curYear.startsWith("1") && (aYear.startsWith("1") || aYear.includes("i"))) return true;
        return false;
      })
      .map((t) => t.section)
      .filter(Boolean);

    if (fromTimetable.length > 0) {
      return Array.from(new Set(fromTimetable)).sort();
    }

    const fromStudents = (data ?? [])
      .filter((s) => {
        const effBatch = s.batch || inferBatchFromRoll(s.rollNumber);
        const effYear = effBatch ? computeYearFromBatch(effBatch) : (s.year || "");
        return effYear.toLowerCase() === rawYear.toLowerCase();
      })
      .map((s) => s.section)
      .filter(Boolean);

    if (fromStudents.length > 0) {
      return Array.from(new Set(fromStudents)).sort();
    }

    return [];
  }, [formCalculatedYear, timetableUploads.data, data]);

  const availableFilterSections = useMemo(() => {
    const fromTimetable = (timetableUploads.data ?? []).map((t) => t.section).filter(Boolean);
    const fromStudents = (data ?? []).map((s) => s.section).filter(Boolean);
    return Array.from(new Set([...(filterOptions?.sections ?? []), ...fromTimetable, ...fromStudents])).sort();
  }, [timetableUploads.data, data, filterOptions?.sections]);

  const openCreateDialog = () => {
    setEditing(null);
    let defaultBatch = 2029;
    if (yearFilter !== ALL) {
      if (yearFilter.includes("1")) defaultBatch = 2030;
      else if (yearFilter.includes("2")) defaultBatch = 2029;
      else if (yearFilter.includes("3")) defaultBatch = 2028;
      else if (yearFilter.includes("4")) defaultBatch = 2027;
    }
    setForm({
      ...emptyForm,
      batch: defaultBatch,
      section: sectionFilter !== ALL ? sectionFilter : (availableFilterSections[0] || "CSE-A"),
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const openEditDialog = (student: StudentItem) => {
    const studentId = student.id || student._id || student.rollNumber;
    setEditing({ ...student, id: studentId });
    setForm({
      name: student.name,
      rollNumber: student.rollNumber,
      batch: Number(student.batch) || 2029,
      branch: student.branch || "CSE",
      section: student.section,
      studentPhone: student.studentPhone || "",
      parentPhone: student.parentPhone || "",
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const validate = (): boolean => {
    const errs: Partial<Record<keyof StudentFormState, string>> = {};
    if (!form.name.trim()) errs.name = "Name is required.";
    if (!form.rollNumber.trim()) errs.rollNumber = "Roll Number is required.";
    if (!form.batch) errs.batch = "Batch graduation year is required.";
    if (!form.branch.trim()) errs.branch = "Branch is required.";
    if (!form.section.trim()) errs.section = "Section is required.";
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        rollNumber: form.rollNumber.trim(),
        batch: Number(form.batch),
        branch: form.branch.trim() || "CSE",
        section: form.section,
        ...(form.studentPhone.trim() ? { studentPhone: form.studentPhone.trim() } : {}),
        ...(form.parentPhone.trim() ? { parentPhone: form.parentPhone.trim() } : {}),
      };

      if (editing) {
        const studentId = editing.id || editing._id || editing.rollNumber;
        await updateStudent(studentId, payload);
        toast.success(`Student "${form.name}" updated successfully.`);
      } else {
        await createStudent(payload);
        toast.success(`Student "${form.name}" added successfully.`);
      }
      setDialogOpen(false);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to save student.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    const studentId = pendingDelete.id || pendingDelete._id || pendingDelete.rollNumber;
    try {
      await deleteStudent(studentId);
      toast.success(`Student "${pendingDelete.name}" deleted.`);
      setPendingDelete(null);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete student.");
    }
  };

  const handleResetStudents = async () => {
    setResetting(true);
    try {
      const res = await resetStudents();
      toast.success(res.message || "Students reset successfully.");
      setResetDialogOpen(false);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to reset students.");
    } finally {
      setResetting(false);
    }
  };

  const handleFileUpload = async (file: File, onProgress: (percent: number) => void) => {
    setUploading(true);
    try {
      const result = await uploadStudentExcel(file, onProgress);
      if ((result.created ?? 0) + (result.updated ?? 0) > 0) reload();
      if (result.status === "error") toast.error(result.message);
      else if (result.status === "warning") toast.warning(result.message);
      else toast.success(result.message || "Students imported successfully!");
      return result;
    } catch (err: any) {
      const message = err.message || "Failed to upload Excel file.";
      toast.error(message);
      return { status: "error" as const, message };
    } finally {
      setUploading(false);
    }
  };

  const columns: Column<StudentItem>[] = [
    {
      key: "rollNumber",
      header: "Roll Number",
      cell: (r) => <span className="font-mono font-semibold text-primary">{r.rollNumber}</span>,
    },
    { key: "name", header: "Student Name" },
    {
      key: "batch",
      header: "Batch",
      cell: (r) => {
        const displayBatch = r.batch || inferBatchFromRoll(r.rollNumber);
        return (
          <span className="font-mono font-medium text-xs bg-muted px-2 py-0.5 rounded">
            {displayBatch || "—"}
          </span>
        );
      },
    },
    {
      key: "year",
      header: "Academic Year",
      cell: (r) => {
        const effBatch = r.batch || inferBatchFromRoll(r.rollNumber);
        const displayYear = effBatch ? computeYearFromBatch(effBatch) : (r.year || "—");
        return (
          <span className="font-medium text-xs text-foreground">
            {displayYear}
          </span>
        );
      },
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
            className="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline hover:text-primary/80 font-medium"
            title={`Call Student (${r.studentPhone})`}
          >
            <Phone className="size-3 text-muted-foreground" />
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
            className="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline hover:text-primary/80 font-medium"
            title={`Call Parent (${r.parentPhone})`}
          >
            <Phone className="size-3 text-muted-foreground" />
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
    {
      key: "actions",
      header: "Actions",
      cell: (r) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openEditDialog(r)}
            title="Edit Student"
          >
            <Pencil className="size-4 text-muted-foreground hover:text-foreground" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setPendingDelete(r)}
            title="Delete Student"
          >
            <Trash2 className="size-4 text-destructive hover:text-destructive/80" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout>
      <PageHeader
        title="Manage Students"
        description="Upload and view uploaded student roster."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={downloadStudentTemplate}>
              <Download className="size-4 mr-2" /> Download Template
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setResetDialogOpen(true)}>
              <RotateCcw className="size-4 mr-2" /> Reset Students
            </Button>
            <Button
              size="sm"
              onClick={() => {
                const yLabel = yearFilter !== ALL ? `_${yearFilter.replace(/\s+/g, "_")}` : "";
                const sLabel = sectionFilter !== ALL ? `_${sectionFilter}` : "";
                exportToCSV(filteredStudents, `Students_Roster${yLabel}${sLabel}`, studentExportColumns);
              }}
              disabled={filteredStudents.length === 0}
              className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs font-semibold gap-1.5"
              title="Export students to Excel/CSV"
            >
              <Download className="size-4 mr-1.5" /> Export Students
            </Button>
          </div>
        }
      />

      <div className="space-y-6">
        {/* Top Card: Upload Students */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Students</CardTitle>
            <CardDescription>
              Upload an Excel file (.xlsx, .xls, .csv) containing student rosters with phone numbers.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload
              accept=".xlsx,.xls,.csv"
              onFileSelect={handleFileUpload}
              uploading={uploading}
              label="Click to browse or drag and drop student roster file (.xlsx, .xls, .csv)"
            />
          </CardContent>
        </Card>

        {/* Bottom Card: Uploaded Students Roster */}
        <Card>
          <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Uploaded Students</CardTitle>
              <CardDescription>
                Filter and view enrolled students across all academic years and sections.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative min-w-[200px]">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search student or roll number..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  className="pl-9"
                />
              </div>

              <div className="w-36">
                <Select value={yearFilter} onValueChange={handleYearFilterChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Years" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>All Years</SelectItem>
                    {(filterOptions?.years ?? []).map((y) => (
                      <SelectItem key={y} value={y}>
                        {y}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="w-36">
                <Select value={sectionFilter} onValueChange={handleSectionFilterChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="All Sections" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>All Sections</SelectItem>
                    {availableFilterSections.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={openCreateDialog} size="sm" className="gap-1.5">
                <Plus className="size-4" /> Add Student
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <LoadingState label="Loading students..." />
            ) : error ? (
              <ErrorState title="Failed to load students" description={error} retry={reload} />
            ) : filteredStudents.length === 0 ? (
              <EmptyState
                title="No students found"
                description={search || yearFilter !== ALL || sectionFilter !== ALL ? "No student matches the filters." : "Get started by uploading an Excel roster or adding a student manually."}
                action={
                  <Button onClick={openCreateDialog} variant="outline" size="sm">
                    <Plus className="size-4 mr-2" /> Add First Student
                  </Button>
                }
              />
            ) : (
              <>
                <DataTable columns={columns} data={filteredStudents} getRowId={(r) => r.id || (r as any)._id || r.rollNumber} showPagination={false} />
                <div className="flex items-center justify-between px-2 text-sm text-muted-foreground">
                  <span>Showing {pageData?.total ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, pageData?.total ?? 0)} of {pageData?.total ?? 0}</span>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button>
                    <span>Page {page} of {Math.max(pageData?.total_pages ?? 0, 1)}</span>
                    <Button size="sm" variant="outline" disabled={page >= (pageData?.total_pages ?? 0)} onClick={() => setPage((value) => value + 1)}>Next</Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Student" : "Add New Student"}</DialogTitle>
            <DialogDescription>
              {editing ? "Update student details." : "Enter student roll number, name, and contact details."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="batch">Batch (Graduation Year) *</Label>
                <ComboboxInput
                  id="batch"
                  type="number"
                  placeholder="e.g. 2029"
                  value={form.batch || ""}
                  onChange={(val) => {
                    const num = Number(val);
                    setForm((prev) => ({ ...prev, batch: isNaN(num) ? prev.batch : num }));
                  }}
                  options={BATCH_OPTIONS.map((b) => ({
                    value: String(b.batch),
                    label: b.label,
                  }))}
                />
                {formErrors.batch && (
                  <p className="text-xs font-medium text-destructive">{formErrors.batch}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Calculated Year</Label>
                <div className="flex h-9 w-full items-center rounded-md border border-input bg-muted/50 px-3 py-1 text-sm font-semibold text-primary">
                  {computeYearFromBatch(form.batch)}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="branch">Branch *</Label>
                <ComboboxInput
                  id="branch"
                  placeholder="e.g. CSE"
                  value={form.branch}
                  onChange={(val) => setForm((prev) => ({ ...prev, branch: val.toUpperCase() }))}
                  options={["CSE", "ECE", "IT", "AIDS", "AIML", "MECH", "CIVIL", "CSBS"]}
                />
                {formErrors.branch && (
                  <p className="text-xs font-medium text-destructive">{formErrors.branch}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="section">Section *</Label>
                <ComboboxInput
                  id="section"
                  placeholder="e.g. CSE-A"
                  value={form.section}
                  onChange={(val) => setForm((prev) => ({ ...prev, section: val.toUpperCase() }))}
                  options={formYearSections}
                  title={`Available sections for ${formCalculatedYear}`}
                />
                {formErrors.section && (
                  <p className="text-xs font-medium text-destructive">{formErrors.section}</p>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rollNumber">Roll Number *</Label>
              <Input
                id="rollNumber"
                placeholder="e.g. 23471A0501"
                value={form.rollNumber}
                onChange={(e) => {
                  const val = e.target.value;
                  const inferred = inferBatchFromRoll(val);
                  setForm({
                    ...form,
                    rollNumber: val,
                    ...(inferred && !editing ? { batch: inferred } : {}),
                  });
                }}
              />
              {formErrors.rollNumber && (
                <p className="text-xs font-medium text-destructive">{formErrors.rollNumber}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="name">Full Name *</Label>
              <Input
                id="name"
                placeholder="e.g. Alex Johnson"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              {formErrors.name && (
                <p className="text-xs font-medium text-destructive">{formErrors.name}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="studentPhone">Student Phone Number</Label>
              <Input
                id="studentPhone"
                placeholder="e.g. +91 9876543210"
                value={form.studentPhone}
                onChange={(e) => setForm({ ...form, studentPhone: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="parentPhone">Parent Phone Number</Label>
              <Input
                id="parentPhone"
                placeholder="e.g. +91 9123456789"
                value={form.parentPhone}
                onChange={(e) => setForm({ ...form, parentPhone: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : editing ? "Update Student" : "Create Student"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete student record for <strong>{pendingDelete?.name}</strong> ({pendingDelete?.rollNumber}).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete Student
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Confirmation */}
      <AlertDialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset Student Roster?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete <strong>ALL students</strong> currently in the database. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={resetting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleResetStudents} disabled={resetting} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              {resetting ? "Resetting..." : "Yes, Reset All Students"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
