import { useMemo, useState, type FormEvent } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Download, Plus, Search, Pencil, Trash2, Filter } from "lucide-react";
import { toast } from "sonner";
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
import {
  createStudent,
  deleteStudent,
  downloadStudentTemplate,
  getStudents,
  updateStudent,
  uploadStudentExcel,
  type StudentItem,
} from "@/services/studentService";
import { MOCK_YEARS } from "@/data/mock/mockData";

export const Route = createFileRoute("/admin/students")({
  head: () => ({
    meta: [
      { title: "Student Management — Admin Portal" },
      { name: "description", content: "Manage student records, register students, or upload Excel rosters." },
    ],
  }),
  component: AdminStudentsPage,
});

const ALL = "ALL";
const SECTIONS = [
  "CSE-A", "CSE-B", "CSE-C", "CSE-D", "CSE-E",
  "CSE-F", "CSE-G", "CSE-H", "CSE-I", "CSE-J"
];

interface StudentFormState {
  name: string;
  rollNumber: string;
  year: string;
  section: string;
  studentPhone: string;
  parentPhone: string;
}

const emptyForm: StudentFormState = {
  name: "",
  rollNumber: "",
  year: "II Year",
  section: "CSE-A",
  studentPhone: "",
  parentPhone: "",
};

function AdminStudentsPage() {
  const [yearFilter, setYearFilter] = useState(ALL);
  const [sectionFilter, setSectionFilter] = useState(ALL);
  const [search, setSearch] = useState("");

  const { data, loading, error, reload } = useAsyncData(
    () => getStudents(yearFilter, sectionFilter, search),
    [yearFilter, sectionFilter, search]
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<StudentItem | null>(null);
  const [form, setForm] = useState<StudentFormState>(emptyForm);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof StudentFormState, string>>>({});
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<StudentItem | null>(null);
  const [uploading, setUploading] = useState(false);

  const openCreateDialog = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormErrors({});
    setDialogOpen(true);
  };

  const openEditDialog = (student: StudentItem) => {
    setEditing(student);
    setForm({
      name: student.name,
      rollNumber: student.rollNumber,
      year: student.year,
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
    if (!form.year.trim()) errs.year = "Year is required.";
    if (!form.section.trim()) errs.section = "Section is required.";
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      if (editing) {
        await updateStudent(editing.id, {
          name: form.name.trim(),
          rollNumber: form.rollNumber.trim(),
          year: form.year,
          section: form.section,
          studentPhone: form.studentPhone.trim() || undefined,
          parentPhone: form.parentPhone.trim() || undefined,
        });
        toast.success(`Student "${form.name}" updated successfully.`);
      } else {
        await createStudent({
          name: form.name.trim(),
          rollNumber: form.rollNumber.trim(),
          year: form.year,
          section: form.section,
          studentPhone: form.studentPhone.trim() || undefined,
          parentPhone: form.parentPhone.trim() || undefined,
        });
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
    try {
      await deleteStudent(pendingDelete.id);
      toast.success(`Student "${pendingDelete.name}" deleted.`);
      setPendingDelete(null);
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete student.");
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const result = await uploadStudentExcel(file);
      toast.success(result.message || "Students imported successfully!");
      reload();
    } catch (err: any) {
      toast.error(err.message || "Failed to upload Excel file.");
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
    { key: "year", header: "Academic Year" },
    { key: "section", header: "Section" },
    {
      key: "studentPhone",
      header: "Student Phone",
      cell: (r) => r.studentPhone || <span className="text-muted-foreground font-mono text-xs">N/A</span>,
    },
    {
      key: "parentPhone",
      header: "Parent Phone",
      cell: (r) => r.parentPhone || <span className="text-muted-foreground font-mono text-xs">N/A</span>,
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
        title="Student Management"
        description="Register students manually or bulk upload class rosters via Excel with phone numbers."
        actions={
          <Button onClick={openCreateDialog}>
            <Plus className="size-4 mr-2" /> Add Student
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Student Roster</CardTitle>
            <CardDescription>
              Filter and view enrolled students across all academic years and sections.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search student or roll number..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                />
              </div>

              <div className="w-36">
                <Select value={yearFilter} onValueChange={setYearFilter}>
                  <SelectTrigger size="sm">
                    <SelectValue placeholder="All Years" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>All Years</SelectItem>
                    {MOCK_YEARS.map((y) => (
                      <SelectItem key={y} value={y}>
                        {y}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="w-36">
                <Select value={sectionFilter} onValueChange={setSectionFilter}>
                  <SelectTrigger size="sm">
                    <SelectValue placeholder="All Sections" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>All Sections</SelectItem>
                    {SECTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {loading ? (
              <LoadingState label="Loading students..." />
            ) : error ? (
              <ErrorState title="Failed to load students" description={error.message} retry={reload} />
            ) : !data || data.length === 0 ? (
              <EmptyState
                title="No students found"
                description={search || yearFilter !== ALL || sectionFilter !== ALL ? "No student matches the filters." : "Get started by adding a student or importing an Excel roster."}
                action={
                  <Button onClick={openCreateDialog} variant="outline" size="sm">
                    <Plus className="size-4 mr-2" /> Add First Student
                  </Button>
                }
              />
            ) : (
              <DataTable columns={columns} data={data} keyExtractor={(r) => r.id} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Bulk Roster Import</CardTitle>
            <CardDescription>
              Upload `.xlsx` roster containing Year, Section, Name, Roll Number, Student Phone, Parent Phone.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={downloadStudentTemplate}
            >
              <Download className="size-4 mr-2" /> Download Template
            </Button>

            <FileUpload
              accept=".xlsx,.xls"
              onFileSelect={handleFileUpload}
              uploading={uploading}
              label="Click to browse or drop student Excel file"
            />
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
                <Label htmlFor="year">Year *</Label>
                <Select value={form.year} onValueChange={(val) => setForm({ ...form, year: val })}>
                  <SelectTrigger id="year">
                    <SelectValue />
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

              <div className="space-y-1.5">
                <Label htmlFor="section">Section *</Label>
                <Select value={form.section} onValueChange={(val) => setForm({ ...form, section: val })}>
                  <SelectTrigger id="section">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SECTIONS.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rollNumber">Roll Number *</Label>
              <Input
                id="rollNumber"
                placeholder="e.g. 21001A0501"
                value={form.rollNumber}
                onChange={(e) => setForm({ ...form, rollNumber: e.target.value })}
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
    </AdminLayout>
  );
}
